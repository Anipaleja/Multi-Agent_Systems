"""3-agent sequential chain pipeline, Mixture-of-Experts variant.

Same shape as `chain3_baseline` and `chain3_optimized`.
Same model bindings and task interface.

Where the MoE layer engages:
1. Suite → expert routing: Based on the suite name (gsm8k, humaneval, etc.),
   route to a specialized expert family (math, swe, research, etc.).
2. Long-context sampling: If the item carries context chunks, the MoEPipeline
   injects expert-aware anchors before sampling, preserving domain-critical
   facts (e.g., citations in research, variable names in code).
3. Critique/revise compression: The planner's plan and the solver's reasoning
   are compressed using domain-aware patterns before being passed to the next
   stage (solver and verifier respectively).

Same quality-floor discipline as optimized: fallback to baseline verifier
prompt if the lean prompt fails to parse.
"""

from __future__ import annotations

import json

from eval.providers import deepseek_client, groq_client, openai_client
from eval.suites import SuiteItem
from token_efficiency_model.combined_tactics.moe_pipeline import MoEPipeline

from .chain3_baseline import (
    PLAN_TEMPLATE,
    SOLVE_TEMPLATE,
    VERIFY_TEMPLATE as BASELINE_VERIFY_TEMPLATE,
    PLANNER_VERIFIER_MODEL,
    PLANNER_VERIFIER_PROVIDER,
    SOLVER_MODEL,
    SOLVER_PROVIDER,
    PLAN_MAX_TOKENS,
    SOLVE_MAX_TOKENS,
    VERIFY_MAX_TOKENS,
    _client_for,
    _coerce_str,
)
from .chain3_optimized import OPTIMIZED_VERIFY_TEMPLATE
from .shape import CallLog, PipelineRun, parse_json_object, usage_to_calllog


SHAPE = "chain3"
VARIANT = "moe"


# Map suite names to expert families for MoE routing.
SUITE_TO_FAMILY = {
    "gsm8k": "math",
    "humaneval": "swe",
    "swe_micro": "swe",
    "mmlu": "multihop",  # mostly factual entity recall
    "hellaswag": "multihop",
    "longctx_qa": "research",  # quoted findings, citations
    "folio": "logical",
    "proofwriter": "logical",
    "logiqa": "logical",
    "bigbench": "operational",  # varied; default
    "mtbench": "operational",
}


# Module-level MoE pipeline singleton (shared across all items in a run).
_moe_pipeline_singleton = MoEPipeline(
    model_backend=None,
    memory_persistence_path="",
    quality_floor=0.98,
)


def _get_task_family(suite: str) -> str:
    """Map suite name to expert family."""
    return SUITE_TO_FAMILY.get(suite, "operational")


def _maybe_sample_long_context_with_moe(item: SuiteItem) -> tuple[str, dict | None]:
    """If the item has candidate chunks, route to MoE expert and sample top-K.

    The MoE expert injects domain-specific anchors before sampling (e.g.,
    (Author, Year) citations in research, variable names in code).

    Returns (effective_task_text, sampling_info). sampling_info is None if no
    sampling was applied.
    """
    if not item.context_chunks or not item.short_task or not item.chunks_target_keep:
        return item.task_text, None

    family = _get_task_family(item.suite)
    chunks = list(item.context_chunks)
    budget = max(1, min(item.chunks_target_keep, len(chunks)))

    try:
        result = _moe_pipeline_singleton.process_task(
            task_text=item.short_task,
            incoming_messages=[],
            prior_context=chunks,
            task_family=family,
            must_keep_facts=None,
        )
    except Exception:
        # If MoE fails for any reason, fall through to raw task.
        return item.task_text, None

    # Recover the sampled/pruned chunks from the expert's debug output.
    inline = result.debug.get("inline_chunks", [])
    pruned = result.debug.get("pruned_context", [])
    kept = [c for c in (inline or pruned or []) if c]

    if not kept or len(kept) == 0:
        return item.task_text, None

    body = ["Read the following passages and answer the question."]
    body.append("")
    body.append("PASSAGES:")
    body.extend(kept)
    body.append("")
    body.append(item.short_task)
    new_task_text = "\n".join(body)

    return new_task_text, {
        "kept_count": len(kept),
        "total_count": len(chunks),
        "budget": budget,
        "expert_id": result.debug.get("expert_id"),
        "quality_proxy": result.debug.get("quality_proxy"),
    }


def _moe_compact_reasoning(reasoning_text: str, family: str, task_text: str) -> str:
    """Pass reasoning through MoE expert's compression."""
    if not reasoning_text:
        return reasoning_text
    # Math reasoning chains are dense — anchors keep numerals, but compression
    # still strips operator/equation glue between them. Bypass for math.
    if family == "math":
        return reasoning_text

    try:
        result = _moe_pipeline_singleton.process_task(
            task_text=task_text,
            incoming_messages=[reasoning_text],
            prior_context=[],
            task_family=family,
        )
    except Exception:
        # If MoE fails, return original reasoning.
        return reasoning_text

    compressed = result.debug.get("compressed_messages")
    # Validate shape: must be a list with at least one element.
    if not isinstance(compressed, list) or len(compressed) < 1:
        return reasoning_text
    return _coerce_str(compressed[0]) or reasoning_text


def run(item: SuiteItem) -> PipelineRun:
    pr = PipelineRun(
        item_id=item.item_id,
        suite=item.suite,
        shape=SHAPE,
        variant=VARIANT,
        final_answer="",
        parse_error=None,
    )

    task_family = _get_task_family(item.suite)

    # 0) MoE-based long-context sampling if applicable.
    effective_task_text, sampling_info = _maybe_sample_long_context_with_moe(item)

    # 1) Plan (same prompt as baseline; planner sees trimmed task on long-ctx items)
    plan_prompt = PLAN_TEMPLATE.format(
        suite_type=item.suite_type,
        answer_format=item.answer_format,
        task_text=effective_task_text,
    )
    plan_result = _client_for(PLANNER_VERIFIER_PROVIDER).call(
        model=PLANNER_VERIFIER_MODEL,
        messages=[{"role": "user", "content": plan_prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=PLAN_MAX_TOKENS,
    )
    plan_obj, plan_err = parse_json_object(plan_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="planner",
            prompt=plan_prompt,
            response_text=plan_result.text,
            usage=plan_result.usage,
            parse_error=plan_err,
        )
    )

    if plan_obj is None:
        plan_text_raw = "(planner produced unparseable output — solver should solve from the task alone)"
        subgoals_text = "(none)"
        approach_note_raw = "(none)"
    else:
        plan_text_raw = _coerce_str(plan_obj.get("plan") or "")
        subgoals_raw = plan_obj.get("subgoals") or []
        if isinstance(subgoals_raw, list):
            subgoals_text = "\n".join(f"- {_coerce_str(s)}" for s in subgoals_raw) or "(none)"
        else:
            subgoals_text = _coerce_str(subgoals_raw)
        approach_note_raw = _coerce_str(plan_obj.get("approach_note") or "")

    # Compress plan + approach note via MoE before they're handed to the solver.
    plan_text = _moe_compact_reasoning(plan_text_raw, task_family, effective_task_text)
    approach_note = _moe_compact_reasoning(approach_note_raw, task_family, effective_task_text)

    # 2) Solve (same prompt as baseline; sees compressed plan)
    solve_prompt = SOLVE_TEMPLATE.format(
        answer_format=item.answer_format,
        task_text=effective_task_text,
        plan_text=plan_text,
        subgoals_text=subgoals_text,
        approach_note=approach_note,
    )
    solve_result = _client_for(SOLVER_PROVIDER).call(
        model=SOLVER_MODEL,
        messages=[{"role": "user", "content": solve_prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=SOLVE_MAX_TOKENS,
    )
    solve_obj, solve_err = parse_json_object(solve_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="solver",
            prompt=solve_prompt,
            response_text=solve_result.text,
            usage=solve_result.usage,
            parse_error=solve_err,
        )
    )

    if solve_obj is None:
        solver_answer = ""
        solver_reasoning_raw = "(solver produced unparseable output)"
        solver_conf = 0.0
    else:
        solver_answer = _coerce_str(solve_obj.get("answer") or "")
        solver_reasoning_raw = _coerce_str(solve_obj.get("reasoning") or "")
        c = solve_obj.get("confidence")
        solver_conf = float(c) if isinstance(c, (int, float)) else 0.0

    # Compress solver reasoning via MoE before it's handed to the verifier.
    solver_reasoning = _moe_compact_reasoning(solver_reasoning_raw, task_family, effective_task_text)

    # 3) Verify — OPTIMIZED prompt with MoE-compressed reasoning
    verify_prompt_optimized = OPTIMIZED_VERIFY_TEMPLATE.format(
        task_text=effective_task_text,
        answer_format=item.answer_format,
        plan_text=plan_text,
        solver_answer=solver_answer,
        solver_reasoning=solver_reasoning,
        solver_conf=solver_conf,
    )
    verify_result = _client_for(PLANNER_VERIFIER_PROVIDER).call(
        model=PLANNER_VERIFIER_MODEL,
        messages=[{"role": "user", "content": verify_prompt_optimized}],
        temperature=0.0,
        seed=42,
        max_tokens=VERIFY_MAX_TOKENS,
    )
    verify_obj, verify_err = parse_json_object(verify_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="verifier",
            prompt=verify_prompt_optimized,
            response_text=verify_result.text,
            usage=verify_result.usage,
            parse_error=verify_err,
        )
    )

    # Quality-floor rollback: if the lean prompt produced unparseable JSON,
    # rerun with the baseline verify prompt and log the rollback.
    if verify_obj is None:
        if solve_obj is None:
            solver_json_payload = json.dumps(
                {"answer": "", "reasoning": "(solver unparseable)", "confidence": 0.0}
            )
        else:
            solver_json_payload = json.dumps(solve_obj)
        rollback_prompt = BASELINE_VERIFY_TEMPLATE.format(
            task_text=effective_task_text,
            answer_format=item.answer_format,
            plan_text=plan_text,
            solver_json=solver_json_payload,
        )
        rollback_result = _client_for(PLANNER_VERIFIER_PROVIDER).call(
            model=PLANNER_VERIFIER_MODEL,
            messages=[{"role": "user", "content": rollback_prompt}],
            temperature=0.0,
            seed=42,
            max_tokens=VERIFY_MAX_TOKENS,
        )
        rollback_obj, rollback_err = parse_json_object(rollback_result.text)
        pr.calls.append(
            usage_to_calllog(
                role="verifier.rollback",
                prompt=rollback_prompt,
                response_text=rollback_result.text,
                usage=rollback_result.usage,
                parse_error=rollback_err,
            )
        )
        verify_obj = rollback_obj
        if verify_obj is None:
            pr.parse_error = f"verify: {verify_err}; rollback: {rollback_err}"
            if solve_obj is not None and isinstance(solve_obj.get("answer"), str):
                pr.final_answer = solve_obj["answer"]
            else:
                pr.final_answer = rollback_result.text.strip()
            return pr

    final = verify_obj.get("final_answer")
    if not isinstance(final, str):
        final = "" if final is None else str(final)
    pr.final_answer = final
    return pr
