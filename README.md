# Multi-Agent Systems (Brevitas)

A focused toolkit and collection of experiments for researching multi-agent AI systems, communication protocols, and token-efficiency techniques.

This repository bundles a local demo environment, benchmarks, and the `token_efficiency_model` library used to measure and reduce redundant token transmission in agent chains.

**Contents**
- `default_testing/` — interactive React demo and token dashboard
- `token_efficiency_model/` — core Python libraries, samplers, compressors, and pipelines
- `eval/` & `eval_runs/` — evaluation pipelines and sample run outputs

**Quick Start**

1. Run the React demo (local Ollama recommended):

```bash
cd default_testing
npm install
npm run dev
```

2. Use the Python experiments and benchmarks:

```bash
source .venv/bin/activate
python -m token_efficiency_model.experiments.run_simulation
```

**High-Level Goals**
- Demonstrate how sequential agent chains generate redundant tokens and measure cost/efficiency.
- Provide modular tooling to experiment with compression, shared-memory middleware, and routing strategies.
- Offer reproducible experiments and visual dashboards for analysis.

**Architecture Overview**

```mermaid
flowchart LR
	User[User / Task] --> A(Architect Agent)
	A --> B(Builder Agent)
	B --> C(Reviewer Agent)
	C --> Result[Final Result]
	subgraph Middleware
		M[Token Efficiency Pipeline]\n(compression, recall, routing)
	end
	A --- M
	B --- M
	C --- M
	M --> Result
```

This diagram highlights the canonical sequential flow (Architect → Builder → Reviewer) with an optional middleware pipeline that can reduce redundant tokens via compression, selective recall, or routing.

See the component-specific README files for deeper details:
- [default_testing/README.md](default_testing/README.md)
- [token_efficiency_model/README.md](token_efficiency_model/README.md)

If you'd like, I can also: add diagrams for the `eval/` pipelines, create a top-level architecture SVG, or generate a short CONTRIBUTING guide.
