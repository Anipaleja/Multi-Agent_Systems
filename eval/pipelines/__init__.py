"""Pipeline shapes. Each module exposes `run(item) -> PipelineRun`."""

from . import (
    chain3_baseline,
    chain3_moe,
    chain3_optimized,
    debate2x2_baseline,
    debate2x2_moe,
    debate2x2_optimized,
    supervisor4_baseline,
    supervisor4_optimized,
    supervisor4_tuned,
    supervisor4_moe,
)
from .shape import CallLog, PipelineRun, parse_json_object, usage_to_calllog

REGISTRY = {
    (supervisor4_baseline.SHAPE, supervisor4_baseline.VARIANT): supervisor4_baseline,
    (supervisor4_optimized.SHAPE, supervisor4_optimized.VARIANT): supervisor4_optimized,
    (supervisor4_tuned.SHAPE, supervisor4_tuned.VARIANT): supervisor4_tuned,
    (supervisor4_moe.SHAPE, supervisor4_moe.VARIANT): supervisor4_moe,
    (chain3_baseline.SHAPE, chain3_baseline.VARIANT): chain3_baseline,
    (chain3_moe.SHAPE, chain3_moe.VARIANT): chain3_moe,
    (chain3_optimized.SHAPE, chain3_optimized.VARIANT): chain3_optimized,
    (debate2x2_baseline.SHAPE, debate2x2_baseline.VARIANT): debate2x2_baseline,
    (debate2x2_moe.SHAPE, debate2x2_moe.VARIANT): debate2x2_moe,
    (debate2x2_optimized.SHAPE, debate2x2_optimized.VARIANT): debate2x2_optimized,
}

__all__ = [
    "CallLog",
    "PipelineRun",
    "REGISTRY",
    "chain3_baseline",
    "chain3_moe",
    "chain3_optimized",
    "debate2x2_baseline",
    "debate2x2_moe",
    "debate2x2_optimized",
    "parse_json_object",
    "supervisor4_baseline",
    "supervisor4_optimized",
    "supervisor4_tuned",
    "supervisor4_moe",
    "usage_to_calllog",
]
