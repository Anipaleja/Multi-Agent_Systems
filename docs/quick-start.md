# Quick Start

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Optional: Ollama for local model-backed flows

## 1) Clone and Prepare Environment

From repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r token_efficiency_model/requirements.txt
```

## 2) Run the Default Testing App

```bash
cd default_testing
npm install
npm run dev
```

If you want the combined launcher from repo root:

```bash
./run_token_efficiency_test.sh
```

This starts:

- Python backend on `http://localhost:5000`
- Vite frontend on `http://localhost:5173`

## 3) Run Evaluation CLI

From repository root:

```bash
python -m eval.cli ping
python -m eval.cli run --suite gsm8k --shape supervisor4 --variant baseline --n 3
python -m eval.cli compare --suite gsm8k --shape supervisor4 --variant moe --n 3
```

Outputs are written to `eval_runs/`.

## 4) Run Token Efficiency Simulations

```bash
cd token_efficiency_model
python experiments/run_simulation.py --episodes 200
python experiments/run_advanced_benchmark.py --episodes 200 --scenario-mix balanced
python experiments/run_delta_benchmark.py
```

## Build This Documentation Locally

Install docs dependencies:

```bash
pip install mkdocs mkdocs-material
```

Serve docs from repo root:

```bash
mkdocs serve
```

Build static site:

```bash
mkdocs build
```
