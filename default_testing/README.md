# Multi-Agent Test Environment

A demonstration environment that simulates three AI agents collaborating on tasks with full token usage tracking. This project demonstrates the token inefficiency that occurs when agents communicate by re-ingesting each other's outputs.

## Purpose

This testing environment simulates the core Nexus middleware problem: showing how much token waste occurs when agents re-establish context independently versus sharing it through a middleware layer.

## Architecture

### The Three Agents

| Agent | Name | Role | Responsibility |
|-------|------|------|----------------|
| 1 | **Architect** | Plans and structures | Breaks the task into components, defines the approach, outputs a structured plan |
| 2 | **Builder** | Executes the plan | Reads Architect's output, implements the core content/solution |
| 3 | **Reviewer** | QA and synthesis | Reads both Architect and Builder outputs, identifies gaps, produces the final polished result |

### Communication Flow

```
User Task
    │
    ▼
[Agent 1: Architect] ──── output ────▶ [Agent 2: Builder]
         │                                      │
         └──────────── both outputs ───────────▶ [Agent 3: Reviewer]
                                                         │
                                                         ▼
                                                  Final Result
```

Agents run sequentially:
- Agent 2 receives Agent 1's full output as context
- Agent 3 receives both Agent 1 and Agent 2's outputs as context

This mirrors a real agent handoff chain and demonstrates token redundancy.

## Local Ollama Mode

This environment now runs **fully locally** using Ollama plus the token_efficiency_model pipeline. No API keys are needed for the current test flow.

| Agent | Ollama Model | Role |
|-------|--------------|------|
| **Agent 1 (Architect)** | `deepseek-r1:8b` | Plans and structures the task |
| **Agent 2 (Builder)** | `qwen2.5:7b` | Executes the plan |
| **Agent 3 (Reviewer)** | `qwen3.5:latest` | Reviews and synthesizes |

This setup allows you to:
- Compare token usage across the local agent chain
- See how the token_efficiency_model pipeline reduces redundant context
- Measure efficiency without any external API dependency

## Setup

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Python 3.10+
- Ollama running locally on `http://127.0.0.1:11434`

### Installation

1. Navigate to the project directory:
```bash
cd default_testing
```

2. Install frontend dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser to the URL shown in the terminal (typically `http://localhost:5173`)

6. Make sure Ollama is running and the models are available:
```bash
ollama serve
ollama pull deepseek-r1:8b
ollama pull qwen2.5:7b
ollama pull qwen3.5:latest
```

## Usage

1. **No API keys are needed**
   - The app runs locally using Ollama and the token_efficiency_model pipeline
   - Each agent maps to one Ollama model: `deepseek-r1:8b`, `qwen2.5:7b`, `qwen3.5:latest`
   - The UI shows token savings from the local execution chain

2. **Select a task** from the dropdown menu:
   - Write a product spec for a note-taking app
   - Design a REST API for a bookstore
   - Create a marketing plan for a new coffee brand
   - Outline a curriculum for teaching Python to beginners

3. **Click "Run Local Agents"** to start the sequential execution
   - Agent 1 (Architect) runs first with `deepseek-r1:8b`
   - Agent 2 (Builder) runs next with `qwen2.5:7b`
   - Agent 3 (Reviewer) runs last with `qwen3.5:latest`

4. **Watch the agents work:**
   - Each agent card shows which provider it's using
   - Agent status updates in real-time (Waiting → Thinking → Complete)
   - Agent outputs appear as they're generated
   - Token usage is tracked for each agent and provider

5. **Review the Token Usage Dashboard** after completion:
   - Total tokens used across all three agents
   - Breakdown of unique vs redundant tokens
   - Efficiency score showing the percentage of wasted tokens
   - Visual breakdown by agent

## Token Tracking

The dashboard tracks:

- **Prompt tokens** — tokens sent in (input)
- **Completion tokens** — tokens generated (output)
- **Total tokens** — sum of all tokens
- **Redundant context tokens** — tokens re-sent from previous agents' outputs
- **Efficiency score** — percentage of unique tokens vs total tokens

### Redundancy Calculation

- Agent 2's prompt includes Agent 1's full output (redundant)
- Agent 3's prompt includes both Agent 1 and Agent 2's outputs (redundant)
- These redundant tokens represent the inefficiency that middleware like Nexus eliminates

## What This Demonstrates

### Token Redundancy Across Multiple Providers

When you run a task, the token dashboard will show that **most tokens consumed are redundant** — prior agents' outputs being re-sent verbatim to downstream agents, even across different AI providers.

**Key Insights:**
- Agent 2 (Groq) re-ingests Agent 1's (DeepSeek) full output as context
- Agent 3 (OpenAI) re-ingests both Agent 1 and Agent 2's outputs
- This redundancy exists regardless of which provider is used
- Different providers have different token counting methods, allowing direct comparison

### Cost Implications

In a production system with thousands of calls per day:
- This redundancy compounds across multiple providers
- Each provider charges differently for tokens
- The dashboard shows exactly where token waste occurs
- A middleware layer like Nexus could eliminate this by maintaining a shared context store

### Provider Comparison

This setup also lets you compare:
- Token efficiency across DeepSeek, Groq, and OpenAI
- Response quality and formatting from different models
- Speed and latency differences
- Cost per task when using different providers

## Tech Stack

- **React** with hooks (useState)
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **Multiple AI Providers**:
  - DeepSeek API (`deepseek-chat`)
  - Groq API (`llama-3.3-70b-versatile`)
  - OpenAI API (`gpt-4o-mini`)

## Model Configuration

- Max tokens per agent: 600
- Sequential execution (not parallel)
- All providers use OpenAI-compatible message format

## File Structure

```
default_testing/
├── src/
│   ├── App.jsx          # Main application component
│   ├── main.jsx         # React entry point
│   └── index.css        # Tailwind directives
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
└── README.md           # This file
```

## Security Note

⚠️ **Never commit your `.env` file to version control.**

- The `.env` file is already listed in `.gitignore`
- API keys are loaded from environment variables at build time
- Keys can also be entered/updated in the UI at runtime
- Never share your actual API keys publicly

**For sharing this project:**
- Share the `.env.example` file (template without actual keys)
- Instruct users to create their own `.env` file with their keys

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## License

This is a demonstration project for the Nexus middleware concept.
