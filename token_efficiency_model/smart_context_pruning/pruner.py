from typing import List, Tuple

from common.utils import lexical_overlap


class SmartContextPruner:
    def __init__(self, budget: int = 5):
        self.budget = max(1, budget)

    def prune(self, task_text: str, context_chunks: List[str]) -> Tuple[List[str], List[float]]:
        if not context_chunks:
            return [], []

        scored = []
        total = len(context_chunks)
        for idx, chunk in enumerate(context_chunks):
            relevance = lexical_overlap(task_text, chunk)
            recency = (idx + 1) / total
            score = 0.75 * relevance + 0.25 * recency
            scored.append((score, idx, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = scored[: self.budget]
        selected.sort(key=lambda item: item[1])

        kept_chunks = [item[2] for item in selected]
        kept_scores = [item[0] for item in selected]
        return kept_chunks, kept_scores
