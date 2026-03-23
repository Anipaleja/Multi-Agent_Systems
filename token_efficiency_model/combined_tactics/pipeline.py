from typing import Callable, Dict, List, Optional

from agent_communication_compression import CommunicationCompressor
from common.metrics import estimate_tokens, estimate_tokens_many, quality_proxy_score, savings_pct
from common.types import PipelineResult, TaskPacket
from custom_protocol import AgentProtocol
from shared_memory_layer import SharedMemoryLayer
from smart_context_pruning import SmartContextPruner
from task_aware_routing import TaskAwareRouter


class TokenEfficientPipeline:
    def __init__(self, model_backend: Optional[Callable[[str, str], str]] = None):
        self.router = TaskAwareRouter()
        self.protocol = AgentProtocol()
        self.memory = SharedMemoryLayer()
        self.model_backend = model_backend or self._default_model_backend

    def _default_model_backend(self, prompt: str, model_name: str) -> str:
        return f"[{model_name}] simulated response to: {prompt[:120]}"

    def process_task(
        self,
        task_text: str,
        incoming_messages: List[str],
        prior_context: List[str],
        task_id: str = "task-001",
        complexity: float = 0.5,
        urgency: float = 0.5,
        compression_level: int = 2,
        prune_budget: int = 5,
        protocol_mode: str = "compact",
    ) -> PipelineResult:
        packet = TaskPacket(
            task_id=task_id,
            task_text=task_text,
            incoming_messages=incoming_messages,
            prior_context=prior_context,
            complexity=complexity,
            urgency=urgency,
        )
        return self.run(packet, compression_level, prune_budget, protocol_mode)

    def run(self, packet: TaskPacket, compression_level: int, prune_budget: int, protocol_mode: str) -> PipelineResult:
        baseline_tokens = estimate_tokens(packet.task_text)
        baseline_tokens += estimate_tokens_many(packet.incoming_messages)
        baseline_tokens += estimate_tokens_many(packet.prior_context)

        compressor = CommunicationCompressor(level=compression_level)
        compressed_messages, compression_stats = compressor.compress_messages(packet.incoming_messages)

        pruner = SmartContextPruner(budget=prune_budget)
        pruned_context, pruning_scores = pruner.prune(packet.task_text, packet.prior_context)

        inline_chunks, context_refs = self.memory.materialize_or_reference(pruned_context + compressed_messages)

        context_load = min(1.0, (len(pruned_context) + len(compressed_messages)) / 15.0)
        route = self.router.route(
            {
                "complexity": packet.complexity,
                "urgency": packet.urgency,
                "context_load": context_load,
            }
        )

        summary = compressed_messages[0] if compressed_messages else packet.task_text[:120]
        payload = self.protocol.build_payload(
            task_id=packet.task_id,
            model=route.model_name,
            summary=summary,
            context_refs=context_refs,
            instructions=packet.task_text,
            priority=packet.urgency,
        )
        protocol_payload = self.protocol.encode(payload, mode=protocol_mode)

        optimized_tokens = estimate_tokens(protocol_payload) + estimate_tokens_many(inline_chunks)
        savings = savings_pct(baseline_tokens, optimized_tokens)

        compression_strength = (compression_level - 1) / 2.0
        prune_strength = max(0.0, min(1.0, 1.0 - (prune_budget / max(1, len(packet.prior_context) or 1))))
        quality = quality_proxy_score(compression_strength, prune_strength, route.route_fit)

        prompt = f"{protocol_payload}\nINLINE_CONTEXT={inline_chunks}"
        model_response = self.model_backend(prompt, route.model_name)

        return PipelineResult(
            routed_model=route.model_name,
            baseline_tokens=baseline_tokens,
            optimized_tokens=optimized_tokens,
            savings_pct=savings,
            quality_proxy=quality,
            protocol_payload=protocol_payload,
            model_response=model_response,
            debug={
                "compression": {
                    "removed_redundant_sentences": compression_stats.removed_redundant_sentences,
                    "original_tokens": compression_stats.original_tokens,
                    "compressed_tokens": compression_stats.compressed_tokens,
                },
                "pruning_scores": pruning_scores,
                "inline_chunks_count": len(inline_chunks),
                "context_refs_count": len(context_refs),
            },
        )
