import argparse
import random
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from combined_tactics import RLTokenOrchestrator, TokenEfficientPipeline
from combined_tactics.rl_orchestrator import RLStep


def synthetic_task(index: int):
    complexity = random.random()
    urgency = random.random()
    context_count = random.randint(4, 14)
    msg_count = random.randint(2, 8)

    task_text = f"Task {index}: analyze architecture constraints and produce execution plan with risks."
    incoming_messages = [
        f"Agent-{i}: We observed repeated handoff context and redundant details in subsystem {i % 3}."
        for i in range(msg_count)
    ]
    prior_context = [
        f"Context-{j}: Prior decision about api contract, deployment dependencies, and monitoring policy {j}."
        for j in range(context_count)
    ]
    context_load = min(1.0, (context_count + msg_count) / 20.0)

    return {
        "task_text": task_text,
        "incoming_messages": incoming_messages,
        "prior_context": prior_context,
        "complexity": complexity,
        "urgency": urgency,
        "context_load": context_load,
    }


def compute_reward(savings_pct: float, quality_proxy: float) -> float:
    return 0.65 * (savings_pct / 100.0) + 0.35 * quality_proxy


def run(episodes: int):
    orchestrator = RLTokenOrchestrator()
    pipeline = TokenEfficientPipeline()

    rewards = []
    savings = []
    quality_scores = []

    for episode in range(episodes):
        task = synthetic_task(episode)
        state = orchestrator.discretize_state(task["complexity"], task["urgency"], task["context_load"])

        action_idx, config = orchestrator.select_action(state, explore=True)
        result = pipeline.process_task(
            task_text=task["task_text"],
            incoming_messages=task["incoming_messages"],
            prior_context=task["prior_context"],
            task_id=f"ep-{episode}",
            complexity=task["complexity"],
            urgency=task["urgency"],
            compression_level=config.compression_level,
            prune_budget=config.prune_budget,
            protocol_mode=config.protocol_mode,
        )

        reward = compute_reward(result.savings_pct, result.quality_proxy)

        next_task = synthetic_task(episode + 1)
        next_state = orchestrator.discretize_state(
            next_task["complexity"], next_task["urgency"], next_task["context_load"]
        )
        orchestrator.update(RLStep(state=state, action_idx=action_idx, reward=reward, next_state=next_state))

        rewards.append(reward)
        savings.append(result.savings_pct)
        quality_scores.append(result.quality_proxy)

    print("=== RL Token Efficiency Simulation ===")
    print(f"Episodes: {episodes}")
    print(f"Avg Reward: {mean(rewards):.4f}")
    print(f"Avg Token Savings (%): {mean(savings):.2f}")
    print(f"Avg Quality Proxy: {mean(quality_scores):.4f}")

    print("\nSample learned policy (first 5 states):")
    shown = 0
    for state, q_values in orchestrator.q_table.items():
        if shown >= 5:
            break
        best_idx = int(q_values.argmax())
        best = orchestrator.actions[best_idx]
        print(
            f"State={state} -> compression={best.compression_level}, prune_budget={best.prune_budget}, "
            f"protocol={best.protocol_mode}"
        )
        shown += 1


def parse_args():
    parser = argparse.ArgumentParser(description="Train and evaluate token-efficiency RL orchestrator")
    parser.add_argument("--episodes", type=int, default=200, help="Number of RL episodes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.episodes)
