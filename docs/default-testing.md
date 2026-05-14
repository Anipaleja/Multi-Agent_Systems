# Default Testing App

The `default_testing/` app is a local demo for sequential 3-agent collaboration with token usage visualization.

## Stack

- Frontend: React + Vite + Tailwind
- Backend: Python API in `default_testing/backend/api.py`

## Agent Flow

The UI simulates:

1. Architect: plans and decomposes task
2. Builder: executes using upstream context
3. Reviewer: synthesizes and validates final output

This intentionally highlights redundant prompt transfer between agents.

## Run Locally

From `default_testing/`:

```bash
npm install
npm run dev
```

From repo root (combined launcher):

```bash
./run_token_efficiency_test.sh
```

## What to Observe

After each run, inspect:

- Prompt vs completion token distribution
- Total token usage per agent
- Redundant context contribution
- Efficiency score trends

## Why It Matters

The app provides an accessible, UI-driven demonstration of why middleware-level context sharing can reduce duplicated token transfer in multi-agent orchestration.
