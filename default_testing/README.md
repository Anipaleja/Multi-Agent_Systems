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

## Multi-Provider Architecture

This environment uses **three different AI providers simultaneously** - each agent is powered by a different provider:

| Agent | Provider | Model | Role |
|-------|----------|-------|------|
| **Agent 1 (Architect)** | DeepSeek | `deepseek-chat` | Plans and structures the task |
| **Agent 2 (Builder)** | Groq | `llama-3.3-70b-versatile` | Executes the plan |
| **Agent 3 (Reviewer)** | OpenAI | `gpt-4o-mini` | Reviews and synthesizes |

This setup allows you to:
- Compare token usage across different AI providers
- See how different models handle the same task in a sequential workflow
- Measure efficiency and cost differences between providers

## Setup

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- API keys for all three providers:
  - DeepSeek API key
  - Groq API key
  - OpenAI API key

### Installation

1. Navigate to the project directory:
```bash
cd default_testing
```

2. Create a `.env` file from the example:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys:
```bash
# Open .env and replace the placeholder values with your actual API keys
VITE_DEEPSEEK_API_KEY=your_deepseek_api_key_here
VITE_GROQ_API_KEY=your_groq_api_key_here
VITE_OPENAI_API_KEY=your_openai_api_key_here
```

**Where to get API keys:**
- DeepSeek: https://platform.deepseek.com/
- Groq: https://console.groq.com/
- OpenAI: https://platform.openai.com/

4. Install dependencies:
```bash
npm install
```

5. Start the development server:
```bash
npm run dev
```

6. Open your browser to the URL shown in the terminal (typically `http://localhost:5173`)

## Usage

1. **API Keys are loaded from your `.env` file**
   - If you set up the `.env` file correctly, the keys will be pre-filled
   - You can also manually enter or update keys in the UI
   - Each field shows which agent will use that provider
   - All three keys are required to run the agents

2. **Select a task** from the dropdown menu:
   - Write a product spec for a note-taking app
   - Design a REST API for a bookstore
   - Create a marketing plan for a new coffee brand
   - Outline a curriculum for teaching Python to beginners

3. **Click "Run Agents"** to start the sequential execution
   - Agent 1 (Architect) runs first using DeepSeek
   - Agent 2 (Builder) runs next using Groq
   - Agent 3 (Reviewer) runs last using OpenAI

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
