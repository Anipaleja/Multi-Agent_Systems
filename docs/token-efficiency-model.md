# Token Efficiency Model

The `token_efficiency_model/` package provides composable tactics to reduce multi-agent token overhead while maintaining quality.

## Core Tactics

- Agent communication compression
- Smart context pruning
- Adaptive semantic sampling
- Shared memory layer
- Task-aware routing
- Custom protocol encoding
- Combined orchestrators (including MoE and RL-aware flows)
- Stateful delta mode for low steady-state transfer

## Package Layout

Key directories:

- `adaptive_semantic_sampling/`
- `agent_communication_compression/`
- `combined_tactics/`
- `common/`
- `custom_protocol/`
- `experts/`
- `shared_memory_layer/`
- `smart_context_pruning/`
- `task_aware_routing/`
- `experiments/`

## Main Entry Point

`combined_tactics/pipeline.py` defines `TokenEfficientPipeline`, which orchestrates:

1. Compression of incoming agent messages
2. Adaptive sampling and pruning of historical context
3. Payload construction via custom protocol
4. Routing to an execution backend
5. Quality-floor fallback and state snapshot persistence

## Delta Communication

`TokenEfficientPipeline.process_task(...)` supports:

- `delta_mode`: use state-delta payloads after warm-up
- `delta_aggressiveness`: controls compactness of computed diffs
- `wire_mode`: JSON or binary protocol modes

This allows near-zero steady-state communication in iterative workflows when state snapshots are available.

## Experiment Scripts

In `token_efficiency_model/experiments/`:

- `run_simulation.py`: baseline simulation loop
- `run_advanced_benchmark.py`: scenario-rich benchmark generation
- `run_delta_benchmark.py`: delta-path focused benchmark

The experiments track tokens, savings percentage, and quality proxies to help tune efficiency settings.
