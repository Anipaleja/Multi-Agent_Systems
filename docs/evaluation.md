# Evaluation Framework

The evaluation stack is centered around `eval/cli.py` and supports smoke checks, single-variant runs, and paired comparisons.

## CLI Commands

## `ping`

Runs a minimal provider connectivity and accounting smoke test.

```bash
python -m eval.cli ping
```

Targets:

- OpenAI (`gpt-4o-mini`)
- DeepSeek (`deepseek-chat`)
- Groq (`llama-3.3-70b-versatile`)

## `run`

Runs one pipeline shape/variant over `n` items in one or more suites.

```bash
python -m eval.cli run --suite gsm8k --shape supervisor4 --variant optimized --n 30
```

Common options:

- `--suite` (repeatable): `mmlu`, `hellaswag`, `gsm8k`, `humaneval`, `longctx_qa`, `bigbench`, `mtbench`, `logiqa`, `proofwriter`, `folio`, `swe_micro`
- `--shape`: defaults to `supervisor4`
- `--variant`: `baseline` or `optimized`
- `--n`: item count
- `--verbose`: prints per-call token and cost logs

## `compare`

Runs paired baseline vs optimized-family variants on the same items.

```bash
python -m eval.cli compare --suite longctx_qa --shape supervisor4 --variant moe --n 30
```

Useful option:

- `--baseline-twice`: measures baseline drift/self-disagreement floor

## Results and Artifacts

Run outputs are serialized into `eval_runs/` as JSON files with suite, shape, variant, token totals, cost totals, and item-level grades.

Use these artifacts for:

- Token and cost trend analysis
- Accuracy delta tracking
- Comparing optimization variants under the same sample set

## Pipeline Variants

Under `eval/pipelines/`, the repository currently includes:

- `chain3_moe.py`
- `debate2x2_moe.py`
- `supervisor4_moe.py`

The `supervisor4_moe.py` pipeline keeps a fixed 4-agent supervisor shape while adding expert-aware routing and context/reasoning optimization.
