# Multi-Agent Systems Documentation

This site documents the **Multi-Agent_Systems** repository and its two core tracks:

- Evaluation pipelines for multi-agent prompting shapes and variants
- Token-efficiency tactics for reducing redundant context transfer

## Repository Overview

Top-level components:

- `default_testing/`: React + Python demo app to run a local 3-agent chain and visualize token usage
- `eval/`: CLI, suites, provider adapters, and pipeline shapes for benchmark-style runs
- `token_efficiency_model/`: Pluggable Python package implementing token-saving tactics
- `eval_runs/`: Stored output JSON from previous benchmark runs
- `run_token_efficiency_test.sh`: Convenience script that starts backend + frontend demo services

## What This Project Demonstrates

In sequential multi-agent systems, downstream agents often re-ingest upstream outputs in full. This creates token overhead that can dominate total cost. The repo explores how to preserve answer quality while reducing this overhead through:

- Communication compression
- Context pruning and semantic sampling
- Shared memory with references
- Structured protocol payloads
- Task-aware routing and MoE variants

## Documentation Map

- **Quick Start**: setup steps and common commands
- **Evaluation Framework**: `eval/cli.py` command usage and run artifacts
- **Token Efficiency Model**: package architecture and pipeline flow
- **Default Testing App**: local UI demo and backend details
