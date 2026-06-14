# brevitas-systems

Token-efficient multi-agent pipeline optimization.

```bash
pip install brevitas-systems
```

```python
from brevitas import optimize
from my_pipeline import architect, builder, reviewer

pipeline = optimize([architect, builder, reviewer])
result = pipeline.run(task)
# ↳ 59% fewer tokens. 47% lower cost. 99% quality parity.
```

## Setup

Generate an API key at [brevitas.systems/dashboard](https://brevitas.systems/dashboard), then either:

```bash
export BREVITAS_API_KEY=bvt_your_key_here
```

or pass it directly:

```python
from brevitas import optimize, configure

configure(api_key="bvt_your_key_here")
pipeline = optimize([architect, builder, reviewer])
```

## How it works

Brevitas wraps your existing agent pipeline and applies five complementary token-reduction tactics on every turn:

| Tactic | What it does |
|---|---|
| **Task-aware routing** | Sends each task to the smallest model that can handle it |
| **Smart context pruning** | Drops low-relevance context before it hits the prompt |
| **Adaptive semantic sampling** | Scores context chunks by relevance, recency, and novelty |
| **Communication compression** | Strips redundancy from inter-agent messages |
| **Shared memory + delta payloads** | Sends only what changed since the last turn |

## API reference

### `optimize(agents, *, api_key=None, **kwargs) → OptimizedPipeline`

Wrap a list of agents in the Brevitas optimization layer.

| Param | Type | Default | Description |
|---|---|---|---|
| `agents` | `list` | required | Agent callables. Each receives the previous agent's output. |
| `api_key` | `str` | env var | Your `bvt_` prefixed API key. |
| `quality_floor` | `float` | `0.98` | Min quality proxy before the pipeline stops compressing. |
| `savings_target` | `float` | `59.0` | Token savings % to target per turn. |
| `compression_level` | `int` | `2` | Message compression aggressiveness (1–3). |
| `prune_budget` | `int` | `5` | Max context items retained per turn. |

### `OptimizedPipeline.run(task, **kwargs) → PipelineResult`

Run a task through the pipeline. Returns a `PipelineResult` with:

- `savings_pct` — tokens saved vs. unoptimized baseline
- `model_response` — concatenated agent outputs
- `baseline_tokens` / `optimized_tokens` — raw counts
- `quality_proxy` — estimated quality retention (0–1)
- `debug` — internal metrics (compression, sampling, pruning)
