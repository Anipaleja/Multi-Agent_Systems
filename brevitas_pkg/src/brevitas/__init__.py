"""brevitas — token-efficient multi-agent pipeline optimization.

Quickstart::

    pip install brevitas-systems

    from brevitas import optimize

    pipeline = optimize([architect, builder, reviewer])
    result = pipeline.run(task)
    # ↳ 59% fewer tokens. 47% lower cost. 99% quality parity.
"""
from __future__ import annotations

import os
from typing import List, Optional, Union, Callable, Any

from ._auth import resolve_key, validate_key
from ._pipeline import OptimizedPipeline, Agent

__version__ = "0.1.0"
__all__ = ["optimize", "configure", "OptimizedPipeline", "__version__"]

_configured_key: Optional[str] = None


def configure(*, api_key: str) -> None:
    """Set the Brevitas API key for this session.

    Alternatively, set the ``BREVITAS_API_KEY`` environment variable.

    Args:
        api_key: Your Brevitas API key (starts with ``bvt_``).
                 Generate one at https://brevitas.systems/dashboard.
    """
    global _configured_key
    validate_key(api_key)
    _configured_key = api_key


def optimize(
    agents: List[Agent],
    *,
    api_key: Optional[str] = None,
    quality_floor: float = 0.98,
    savings_target: float = 59.0,
    compression_level: int = 2,
    prune_budget: int = 5,
    protocol_mode: str = "compact",
    delta_mode: str = "on",
) -> OptimizedPipeline:
    """Wrap *agents* in a token-efficient pipeline.

    Args:
        agents: List of agent callables. Each agent receives the previous
                agent's output (or the raw task on the first turn) and
                should return a string response.
        api_key: Your Brevitas API key. Falls back to the key set via
                 :func:`configure` or the ``BREVITAS_API_KEY`` env var.
        quality_floor: Minimum acceptable quality proxy (0–1). The pipeline
                       will not compress below this threshold.
        savings_target: Token savings percentage to target (default 59%).
        compression_level: Message compression aggressiveness (1–3).
        prune_budget: Maximum context items to retain per turn.
        protocol_mode: Wire protocol mode — ``"compact"`` or ``"verbose"``.
        delta_mode: Whether to send delta payloads between turns
                    (``"on"``/``"off"``).

    Returns:
        An :class:`OptimizedPipeline` whose :meth:`~OptimizedPipeline.run`
        method accepts a task string and returns a
        :class:`~brevitas._engine.common.types.PipelineResult`.

    Example::

        from brevitas import optimize
        from my_pipeline import architect, builder, reviewer

        pipeline = optimize([architect, builder, reviewer])
        result = pipeline.run(task)
        # ↳ 59% fewer tokens. 47% lower cost. 99% quality parity.
    """
    key = api_key or _configured_key or None
    resolved = resolve_key(key)
    validate_key(resolved)

    return OptimizedPipeline(
        agents=agents,
        quality_floor=quality_floor,
        savings_target=savings_target,
        compression_level=compression_level,
        prune_budget=prune_budget,
        protocol_mode=protocol_mode,
        delta_mode=delta_mode,
    )
