"""OptimizedPipeline — the object returned by optimize()."""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Union

from ._engine.combined_tactics.pipeline import TokenEfficientPipeline
from ._engine.common.types import PipelineResult


# An "agent" is any callable or object with a __call__ / run method.
Agent = Union[Callable[..., Any], Any]


class OptimizedPipeline:
    """A token-efficient wrapper around a list of agents.

    Returned by :func:`brevitas.optimize`. Call :meth:`run` with a task
    string to execute the pipeline with Brevitas token optimizations applied.

    Example::

        pipeline = optimize([architect, builder, reviewer])
        result = pipeline.run("Build me a REST API in FastAPI")
        print(f"↳ {result.savings_pct:.0f}% fewer tokens.")
    """

    def __init__(
        self,
        agents: List[Agent],
        *,
        quality_floor: float = 0.98,
        savings_target: float = 59.0,
        compression_level: int = 2,
        prune_budget: int = 5,
        protocol_mode: str = "compact",
        delta_mode: str = "on",
    ) -> None:
        self._agents = agents
        self._compression_level = compression_level
        self._prune_budget = prune_budget
        self._protocol_mode = protocol_mode
        self._delta_mode = delta_mode
        self._pipeline = TokenEfficientPipeline(
            model_backend=self._dispatch,
            quality_floor=quality_floor,
            savings_target=savings_target,
        )
        self._prior_context: List[str] = []

    def _dispatch(self, prompt: str, model_name: str) -> str:
        """Fan the prompt out to each agent sequentially and collect responses."""
        responses: List[str] = []
        payload = prompt
        for agent in self._agents:
            if callable(agent):
                out = agent(payload)
            elif hasattr(agent, "run"):
                out = agent.run(payload)
            elif hasattr(agent, "invoke"):
                out = agent.invoke(payload)
            else:
                out = str(agent)
            responses.append(str(out) if out is not None else "")
            payload = responses[-1]
        return "\n".join(responses)

    def run(
        self,
        task: str,
        *,
        incoming_messages: Optional[List[str]] = None,
        complexity: float = 0.5,
        urgency: float = 0.5,
        task_id: str = "brevitas-task",
    ) -> PipelineResult:
        """Run *task* through the optimized pipeline.

        Args:
            task: The task description / prompt for the agent pipeline.
            incoming_messages: Optional additional messages to include.
            complexity: 0–1 hint about task complexity (affects compression).
            urgency: 0–1 hint about urgency (affects context retention).
            task_id: Stable identifier for this task (used for delta caching).

        Returns:
            :class:`PipelineResult` with ``savings_pct``, ``model_response``,
            token counts, and a ``debug`` dict with internals.
        """
        result = self._pipeline.process_task(
            task_text=task,
            incoming_messages=incoming_messages or [],
            prior_context=self._prior_context,
            task_id=task_id,
            complexity=complexity,
            urgency=urgency,
            compression_level=self._compression_level,
            prune_budget=self._prune_budget,
            protocol_mode=self._protocol_mode,
            delta_mode=self._delta_mode,
        )
        # Accumulate context across turns for stateful pipelines.
        self._prior_context.append(result.model_response)
        if len(self._prior_context) > 20:
            self._prior_context = self._prior_context[-20:]
        return result
