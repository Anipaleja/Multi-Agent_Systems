# Multi-Agent Systems

A repository for exploring and demonstrating multi-agent AI systems, communication patterns, and token efficiency analysis.

## Projects

### Default Testing Environment

Located in `default_testing/`, this is a self-contained React application that demonstrates how three AI agents collaborate on tasks with full token usage tracking.

**Key Features:**
- Three specialized agents (Architect, Builder, Reviewer) working sequentially
- Real-time token usage tracking and visualization
- Demonstration of token redundancy in multi-agent systems
- Interactive dashboard showing efficiency metrics

**Get Started:**
```bash
cd default_testing
npm install
npm run dev
```

See [default_testing/README.md](./default_testing/README.md) for detailed documentation.

## Purpose

This repository demonstrates the core challenges in multi-agent systems, particularly:
- Token inefficiency when agents re-ingest each other's outputs
- Communication patterns between sequential agents
- Real-world cost implications of redundant context in production systems

## What This Demonstrates

The testing environment shows that in a typical sequential agent chain, the majority of tokens consumed are **redundant** — previous agents' outputs being re-sent verbatim to downstream agents. This redundancy represents significant API costs in production systems.
