"""Command-line entry point for the eval/ stack.

Subcommands:
  ping    one-token smoke test across all providers
  run     run a suite x shape x variant at n items
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python -m eval.cli` and `python eval/cli.py` to both work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Best-effort .env loader — no python-dotenv dependency required.
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    import os
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


from eval.providers import ProviderResponseError  # noqa: E402
from eval.providers import deepseek_client, groq_client, openai_client  # noqa: E402


PING_MESSAGES = [
    {
        "role": "user",
        "content": "Reply with the single word: pong",
    }
]


def _row(label: str, result) -> dict:
    u = result.usage
    return {
        "label": label,
        "provider": u.provider,
        "model": u.model,
        "response_text": result.text.strip(),
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "total_tokens": u.total_tokens,
        "latency_ms": round(u.latency_ms, 1),
        "cost_usd": round(u.cost_usd, 8),
        "seed": u.seed,
        "temperature": u.temperature,
    }


def cmd_ping(_args: argparse.Namespace) -> int:
    targets = [
        ("openai/gpt-4o-mini", openai_client.call,   {"model": "gpt-4o-mini"}),
        ("deepseek/deepseek-chat", deepseek_client.call, {"model": "deepseek-chat"}),
        ("groq/llama-3.3-70b-versatile", groq_client.call, {"model": "llama-3.3-70b-versatile"}),
    ]

    rows: list[dict] = []
    failures: list[tuple[str, str]] = []

    for label, fn, kwargs in targets:
        try:
            result = fn(messages=PING_MESSAGES, max_tokens=8, **kwargs)
        except ProviderResponseError as exc:
            failures.append((label, str(exc)))
            continue
        rows.append(_row(label, result))

    print("\n=== Phase 3a smoke: per-provider ping ===\n")
    headers = [
        "label",
        "provider",
        "model",
        "response_text",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "latency_ms",
        "cost_usd",
    ]
    for row in rows:
        for h in headers:
            print(f"  {h:>20s} : {row[h]}")
        print()

    if failures:
        print("FAILURES:")
        for label, msg in failures:
            print(f"  {label}: {msg}")
        return 1

    # Also dump the raw rows as JSON so the user can inspect / archive.
    print("--- JSON ---")
    print(json.dumps(rows, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from eval.runner import run_suite, write_run_json

    suites = args.suite if args.suite else ["mmlu", "hellaswag", "gsm8k", "humaneval"]
    out_dir = Path(__file__).resolve().parent.parent / "eval_runs"

    overall_correct = 0
    overall_n = 0
    overall_tokens = 0
    overall_cost = 0.0

    for suite in suites:
        print(f"\n=== {suite} | {args.shape}/{args.variant} | n={args.n} ===")
        result = run_suite(suite=suite, shape=args.shape, variant=args.variant, n=args.n)
        path = write_run_json(result, out_dir)
        for t in result.tasks:
            mark = "PASS" if t.grade.is_correct else "FAIL"
            pe = f"  parse_error={t.grade.parse_error}" if t.grade.parse_error else ""
            print(
                f"  [{mark}] {t.item.item_id}  gold={t.item.gold!r:<10}  "
                f"predicted={t.grade.predicted_canonical!r:<14}  "
                f"tokens={t.run.total_tokens:>5}  cost=${t.run.total_cost_usd:.6f}  "
                f"wall={t.wall_time_ms:.0f}ms{pe}"
            )
            if args.verbose:
                for c in t.run.calls:
                    print(
                        f"      {c.role:>22s}  {c.provider}/{c.model}  "
                        f"in={c.prompt_tokens} out={c.completion_tokens} "
                        f"latency={c.latency_ms:.0f}ms  cost=${c.cost_usd:.7f}"
                    )
        print(
            f"  --- accuracy={result.n_correct}/{result.n} ({result.accuracy*100:.1f}%)  "
            f"tokens={result.total_tokens}  cost=${result.total_cost_usd:.5f}  "
            f"saved -> {path.name}"
        )
        overall_correct += result.n_correct
        overall_n += result.n
        overall_tokens += result.total_tokens
        overall_cost += result.total_cost_usd

    print(
        f"\n=== overall: {overall_correct}/{overall_n} "
        f"({(overall_correct/overall_n*100 if overall_n else 0):.1f}%)  "
        f"tokens={overall_tokens}  cost=${overall_cost:.5f} ==="
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    ping = sub.add_parser("ping", help="One-token-each smoke test on all 3 providers.")
    ping.set_defaults(func=cmd_ping)

    run = sub.add_parser("run", help="Run a suite x pipeline at n items.")
    run.add_argument("--suite", action="append", choices=["mmlu", "hellaswag", "gsm8k", "humaneval", "longctx_qa", "bigbench", "mtbench", "logiqa", "proofwriter", "folio", "swe_micro"],
                     help="One or more suite names; default = all four.")
    run.add_argument("--shape", default="supervisor4")
    run.add_argument("--variant", default="baseline", choices=["baseline", "optimized"])
    run.add_argument("--n", type=int, default=3)
    run.add_argument("--verbose", action="store_true",
                     help="Print every per-call usage row.")
    run.set_defaults(func=cmd_run)

    cmp_ = sub.add_parser("compare", help="Run baseline vs optimized on the same items, paired.")
    cmp_.add_argument("--suite", action="append", choices=["mmlu", "hellaswag", "gsm8k", "humaneval", "longctx_qa", "bigbench", "mtbench", "logiqa", "proofwriter", "folio", "swe_micro"])
    cmp_.add_argument("--shape", default="supervisor4")
    cmp_.add_argument("--variant", default="optimized", choices=["optimized", "tuned", "moe"],
                      help="Which optimized variant to compare baseline against.")
    cmp_.add_argument("--n", type=int, default=3)
    cmp_.add_argument("--baseline-twice", action="store_true",
                      help="Run baseline pipeline twice per item to measure provider drift.")
    cmp_.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return int(args.func(args))


def cmd_compare(args: argparse.Namespace) -> int:
    from eval.runner import run_paired, write_paired_json

    suites = args.suite if args.suite else [
        "mmlu", "hellaswag", "gsm8k", "humaneval", "longctx_qa", "bigbench", "mtbench"
    ]
    out_dir = Path(__file__).resolve().parent.parent / "eval_runs"

    grand_b_correct = grand_o_correct = grand_n = 0
    grand_b_tokens = grand_o_tokens = 0
    grand_b_cost = grand_o_cost = 0.0
    grand_b2_disagree = grand_b2_n = 0

    def _progress(done: int, total: int, paired) -> None:
        bt = sum(p.baseline.run.total_tokens for p in paired.pairs)
        ot = sum(p.optimized.run.total_tokens for p in paired.pairs)
        red = (bt - ot) / bt * 100.0 if bt else 0.0
        bcost = sum(p.baseline.run.total_cost_usd for p in paired.pairs)
        ocost = sum(p.optimized.run.total_cost_usd for p in paired.pairs)
        print(
            f"    [{done:>3}/{total}]  running tokens b={bt} o={ot}  "
            f"reduction {red:>+5.1f}%  cost b=${bcost:.4f} o=${ocost:.4f}",
            flush=True,
        )

    for suite in suites:
        print(f"\n=== {suite} | paired baseline vs optimized | n={args.n}"
              f"{' | baseline-twice' if args.baseline_twice else ''} ===")
        result = run_paired(
            suite=suite,
            n=args.n,
            shape=args.shape,
            variant=args.variant,
            baseline_twice=args.baseline_twice,
            progress_cb=_progress,
        )
        path = write_paired_json(result, out_dir)

        # Per-task table
        print(f"  {'item_id':<26}  {'b/o':<5}  {'b_tok':>6}  {'o_tok':>6}  {'red%':>7}  {'b_cost':>9}  {'o_cost':>9}")
        for pt in result.pairs:
            b_ok = "Y" if pt.baseline.grade.is_correct else "N"
            o_ok = "Y" if pt.optimized.grade.is_correct else "N"
            bt = pt.baseline.run.total_tokens
            ot = pt.optimized.run.total_tokens
            red = (bt - ot) / bt * 100.0 if bt else 0.0
            print(
                f"  {pt.item.item_id:<26}  {b_ok}/{o_ok:<3}  "
                f"{bt:>6}  {ot:>6}  {red:>6.1f}%  "
                f"${pt.baseline.run.total_cost_usd:>8.6f}  ${pt.optimized.run.total_cost_usd:>8.6f}"
            )

        # Summary
        print(
            f"  --- baseline: {result.baseline_correct}/{result.n} ({result.baseline_accuracy*100:.1f}%)  "
            f"tokens={result.baseline_tokens}  cost=${result.baseline_cost_usd:.5f}"
        )
        if result.has_baseline2:
            print(
                f"  --- baseline2:{result.baseline2_correct}/{result.n} "
                f"({(result.baseline2_correct/result.n*100):.1f}%)  "
                f"tokens={result.baseline2_tokens}  cost=${result.baseline2_cost_usd:.5f}  "
                f"self-disagree={result.baseline_self_disagree}/{result.n} "
                f"({result.baseline_self_disagree/result.n*100:.1f}%)"
            )
        print(
            f"  --- optimized:{result.optimized_correct}/{result.n} ({result.optimized_accuracy*100:.1f}%)  "
            f"tokens={result.optimized_tokens}  cost=${result.optimized_cost_usd:.5f}"
        )
        print(
            f"  --- delta:   acc {result.accuracy_delta*100:+.1f}pp  "
            f"(broken={result.n_broken} fixed={result.n_fixed}, McNemar p={result.mcnemar_two_sided_p():.3f})"
        )
        print(
            f"  --- savings: tokens -{result.token_reduction_pct:.1f}%  "
            f"cost -{result.cost_reduction_pct:.1f}%  saved -> {path.name}"
        )

        grand_n += result.n
        grand_b_correct += result.baseline_correct
        grand_o_correct += result.optimized_correct
        grand_b_tokens += result.baseline_tokens
        grand_o_tokens += result.optimized_tokens
        grand_b_cost += result.baseline_cost_usd
        grand_o_cost += result.optimized_cost_usd
        if result.has_baseline2:
            grand_b2_disagree += result.baseline_self_disagree
            grand_b2_n += result.n

    if grand_n:
        token_red = (grand_b_tokens - grand_o_tokens) / grand_b_tokens * 100.0 if grand_b_tokens else 0.0
        cost_red = (grand_b_cost - grand_o_cost) / grand_b_cost * 100.0 if grand_b_cost else 0.0
        print(
            f"\n=== overall paired: "
            f"baseline {grand_b_correct}/{grand_n} ({grand_b_correct/grand_n*100:.1f}%)  "
            f"vs  optimized {grand_o_correct}/{grand_n} ({grand_o_correct/grand_n*100:.1f}%)  "
            f"|  tokens -{token_red:.1f}%  |  cost -{cost_red:.1f}% ==="
        )
        if grand_b2_n:
            print(
                f"=== baseline self-disagreement: {grand_b2_disagree}/{grand_b2_n} "
                f"({grand_b2_disagree/grand_b2_n*100:.1f}%) — interpret accuracy delta against this floor ==="
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
