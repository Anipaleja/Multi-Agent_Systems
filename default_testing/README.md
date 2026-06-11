# Multi-Agent Test Environment (default_testing)

An interactive demo that simulates three cooperating agents and visualizes token usage and redundancy. Use this as a hands-on playground to explore how agent handoffs create redundant context and how middleware or compression strategies reduce token cost.

## Key Concepts
- Three-agent sequential pipeline: Architect → Builder → Reviewer
- Token accounting for each agent: prompt, completion, and redundant tokens
- Middleware pipeline (optional) that compresses, recalls, and routes context

```mermaid
flowchart TD
  User[User Task] --> A[Architect]\n  A --> B[Builder]\n+  B --> C[Reviewer]\n+  C --> Final[Final Result]
  subgraph Tracking
    T(Token Dashboard) --- A
    T --- B
    T --- C
  end
```

## Architecture & Token Flow

```mermaid
sequenceDiagram
  participant U as User
  participant A as Architect
  participant B as Builder
  participant R as Reviewer
  participant M as Middleware

  U->>A: Task prompt
  A-->>B: Full output (context)
  B-->>R: Full outputs (A + B)
  Note over A,B,R: Dashboard counts: prompt / completion / redundant
  A->>M: Optional compression/recall
  B->>M: Optional compression/recall
  R->>M: Optional compression/recall
```

This highlights where redundant tokens are produced: when Agent B re-sends A's output and Agent R re-sends both A's and B's outputs.

## Setup (Local Ollama recommended)

Prerequisites:
- Node.js 18+
- npm or yarn
- Python 3.10+
- (Optional) Ollama for local models

Install and run:

```bash
cd default_testing
npm install
npm run dev
```

If using Ollama locally, start and pull models:

```bash
ollama serve
ollama pull deepseek-r1:8b
ollama pull qwen2.5:7b
ollama pull qwen3.5:latest
```

## Usage

- Open the UI (typically at `http://localhost:5173`).
- Select a task and click `Run Local Agents`.
- Observe per-agent token counts and the token-efficiency dashboard.

### Dashboard Metrics
- Prompt tokens: tokens sent to the model
- Completion tokens: tokens produced by the model
- Redundant tokens: tokens re-sent from earlier agents' outputs
- Efficiency score: unique tokens / total tokens

## Files of Interest
- `src/App.jsx` — demo UI and agent orchestration
- `src/TokenEfficiencyPanel.jsx` — dashboard visualizations

## Extending the Demo

- Swap local models (Ollama) to experiment with model behavior.
- Toggle the middleware pipeline to measure savings from compression and recall.
- Feed custom tasks via the UI or modify `default_testing/src/advancedTasks.json`.

## License
This demo is provided for research and demonstration purposes.
