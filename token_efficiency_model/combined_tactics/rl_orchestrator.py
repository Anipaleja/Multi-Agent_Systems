import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from common.types import TacticConfig


@dataclass
class RLStep:
    state: Tuple[int, int, int]
    action_idx: int
    reward: float
    next_state: Tuple[int, int, int]


class RLTokenOrchestrator:
    def __init__(self, alpha: float = 0.15, gamma: float = 0.92, epsilon: float = 0.12):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.actions = self._build_actions()
        self.q_table: Dict[Tuple[int, int, int], np.ndarray] = {}

    def _build_actions(self) -> List[TacticConfig]:
        actions = []
        for compression_level in [1, 2, 3]:
            for prune_budget in [3, 5, 8]:
                for protocol_mode in ["compact", "raw-json"]:
                    actions.append(
                        TacticConfig(
                            compression_level=compression_level,
                            prune_budget=prune_budget,
                            protocol_mode=protocol_mode,
                            use_shared_memory=True,
                        )
                    )
        return actions

    def discretize_state(self, complexity: float, urgency: float, context_load: float) -> Tuple[int, int, int]:
        c_bin = min(2, int(complexity * 3))
        u_bin = min(2, int(urgency * 3))
        l_bin = min(2, int(context_load * 3))
        return c_bin, u_bin, l_bin

    def _ensure_state(self, state: Tuple[int, int, int]) -> None:
        if state not in self.q_table:
            self.q_table[state] = np.zeros(len(self.actions), dtype=float)

    def select_action(self, state: Tuple[int, int, int], explore: bool = True) -> Tuple[int, TacticConfig]:
        self._ensure_state(state)
        if explore and random.random() < self.epsilon:
            action_idx = random.randrange(len(self.actions))
            return action_idx, self.actions[action_idx]

        q_values = self.q_table[state]
        action_idx = int(np.argmax(q_values))
        return action_idx, self.actions[action_idx]

    def update(self, step: RLStep) -> None:
        self._ensure_state(step.state)
        self._ensure_state(step.next_state)

        current_q = self.q_table[step.state][step.action_idx]
        max_next = float(np.max(self.q_table[step.next_state]))
        updated = current_q + self.alpha * (step.reward + self.gamma * max_next - current_q)
        self.q_table[step.state][step.action_idx] = updated
