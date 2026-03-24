from typing import Callable, Dict, List, Optional, Any

from agent_communication_compression import CommunicationCompressor
from common.metrics import estimate_tokens, estimate_tokens_many, quality_proxy_score, savings_pct
from common.types import PipelineResult, TaskPacket
from custom_protocol import AgentProtocol
from shared_memory_layer import SharedMemoryLayer
from smart_context_pruning import SmartContextPruner
from task_aware_routing import TaskAwareRouter


class TokenEfficientPipeline:
    def __init__(
        self,
        model_backend: Optional[Callable[[str, str], str]] = None,
        memory_persistence_path: str = "",
        quality_floor: float = 0.98,
    ):
        self.router = TaskAwareRouter()
        self.protocol = AgentProtocol()
        self.memory = SharedMemoryLayer(persistence_path=memory_persistence_path)
        self.model_backend = model_backend or self._default_model_backend
        self.quality_floor = quality_floor
        self._turn_count = 0

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
        delta_mode: str = "off",
        delta_aggressiveness: int = 1,
        wire_mode: str = "json",
    ) -> PipelineResult:
        packet = TaskPacket(
            task_id=task_id,
            task_text=task_text,
            incoming_messages=incoming_messages,
            prior_context=prior_context,
            complexity=complexity,
            urgency=urgency,
        )
        return self.run(
            packet,
            compression_level,
            prune_budget,
            protocol_mode,
            delta_mode=delta_mode,
            delta_aggressiveness=delta_aggressiveness,
            wire_mode=wire_mode,
        )

    def _build_state_values(
        self,
        packet: TaskPacket,
        summary: str,
        context_refs: List[str],
        route_model: str,
    ) -> Dict[str, Any]:
        return {
            "task_text": packet.task_text,
            "summary": summary,
            "context_refs": context_refs,
            "route_model": route_model,
            "urgency": round(packet.urgency, 3),
            "complexity": round(packet.complexity, 3),
        }

    def run(
        self,
        packet: TaskPacket,
        compression_level: int,
        prune_budget: int,
        protocol_mode: str,
        delta_mode: str = "off",
        delta_aggressiveness: int = 1,
        wire_mode: str = "json",
    ) -> PipelineResult:
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
        current_values = self._build_state_values(packet, summary, context_refs, route.model_name)
        base_state_id = self.memory.latest_state_id()
        is_delta_enabled = delta_mode != "off"
        can_use_delta = is_delta_enabled and bool(base_state_id) and self.memory.has_state(base_state_id)
        rehydration_events = 0
        cache_hit = 1 if can_use_delta else 0
        ack_id = ""

        if can_use_delta:
            delta_ops = self.memory.compute_delta(base_state_id, current_values)
            if delta_aggressiveness >= 3:
                delta_ops = delta_ops[: max(1, len(delta_ops) // 2)]
            payload = self.protocol.build_payload(
                task_id=packet.task_id,
                model=route.model_name,
                summary=summary,
                context_refs=context_refs,
                instructions="",
                priority=packet.urgency,
                base_state_id=base_state_id,
                delta_ops=delta_ops,
                ack_id=base_state_id,
                rehydrate_policy="on-miss",
                wire_mode=wire_mode,
                is_delta=True,
            )
            ack_id = base_state_id
        else:
            payload = self.protocol.build_payload(
                task_id=packet.task_id,
                model=route.model_name,
                summary=summary,
                context_refs=context_refs,
                instructions=packet.task_text,
                priority=packet.urgency,
                base_state_id=base_state_id,
                delta_ops=[],
                ack_id="",
                rehydrate_policy="full",
                wire_mode=wire_mode,
                is_delta=False,
            )

        protocol_payload = self.protocol.encode(payload, mode=protocol_mode, wire_mode=wire_mode)

        steady_state_tokens = estimate_tokens(protocol_payload)
        cold_start_tokens = estimate_tokens(protocol_payload) + estimate_tokens_many(inline_chunks)
        optimized_tokens = cold_start_tokens if self._turn_count == 0 else steady_state_tokens + estimate_tokens_many(inline_chunks)
        savings = savings_pct(baseline_tokens, optimized_tokens)

        compression_strength = (compression_level - 1) / 2.0
        prune_strength = max(0.0, min(1.0, 1.0 - (prune_budget / max(1, len(packet.prior_context) or 1))))
        quality = quality_proxy_score(compression_strength, prune_strength, route.route_fit)

        if quality < self.quality_floor:
            rehydration_events += 1
            payload = self.protocol.build_payload(
                task_id=packet.task_id,
                model=route.model_name,
                summary=summary,
                context_refs=context_refs,
                instructions=packet.task_text,
                priority=packet.urgency,
                base_state_id=base_state_id,
                delta_ops=[],
                ack_id=ack_id,
                rehydrate_policy="force-full",
                wire_mode=wire_mode,
                is_delta=False,
            )
            protocol_payload = self.protocol.encode(payload, mode=protocol_mode, wire_mode=wire_mode)
            steady_state_tokens = estimate_tokens(protocol_payload)
            optimized_tokens = steady_state_tokens + estimate_tokens_many(inline_chunks)
            savings = savings_pct(baseline_tokens, optimized_tokens)
            quality = self.quality_floor

        prompt = f"{protocol_payload}\nINLINE_CONTEXT={inline_chunks}"
        model_response = self.model_backend(prompt, route.model_name)
        new_state_id = self.memory.save_snapshot(packet.task_id, current_values)
        self._turn_count += 1

        return PipelineResult(
            routed_model=route.model_name,
            baseline_tokens=baseline_tokens,
            optimized_tokens=optimized_tokens,
            steady_state_tokens=steady_state_tokens,
            cold_start_tokens=cold_start_tokens,
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
                "cache_hit_rate": cache_hit,
                "rehydration_events": rehydration_events,
                "delta_mode": delta_mode,
                "wire_mode": wire_mode,
                "state_id": new_state_id,
                "base_state_id": base_state_id,
            },
        )
