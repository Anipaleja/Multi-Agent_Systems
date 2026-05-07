"""4-agent supervisor pipeline, Mixture-of-Experts variant.

Same shape as `supervisor4_baseline` and `supervisor4_optimized`.
Same model bindings and task interface.

Where the MoE layer engages:
1. Suite → expert routing: Based on the suite name (gsm8k, humaneval, etc.),
   route to a specialized expert family (math, swe, research, etc.).
2. Long-context sampling: If the item carries context chunks, the MoEPipeline
   injects expert-aware anchors before sampling, preserving domain-critical
   facts (e.g., citations in research, variable names in code).
3. Worker reasoning compression: The 3 worker reasoning strings are passed
   through the MoEPipeline with the routed expert, which compresses them
   using domain-aware patterns.

Same quality-floor discipline as optimized: fallback to baseline synth
prompt if the lean prompt fails to parse.
"""

from __future__ import annotations

import concurrent.futures
import json

from eval.providers import deepseek_client, openai_client
from eval.suites import SuiteItem
from token_efficiency_model.combined_tactics.moe_pipeline import MoEPipeline

from .shape import CallLog, PipelineRun, parse_json_object, usage_to_calllog
from .supervisor4_baseline import (
    DECOMPOSE_TEMPLATE,
    SUPERVISOR_MODEL,
    SUPERVISOR_PROVIDER,
    SYNTHESIZE_TEMPLATE as BASELINE_SYNTHESIZE_TEMPLATE,
    WORKER_MODEL,
    WORKER_PROVIDER,
    WORKER_TEMPLATE,
    DECOMPOSE_MAX_TOKENS,
    WORKER_MAX_TOKENS,
    SYNTHESIZE_MAX_TOKENS,
    _client_for,
)
from .supervisor4_optimized import OPTIMIZED_SYNTHESIZE_TEMPLATE


SHAPE = "supervisor4"
VARIANT = "moe"


# Map suite names to expert families for MoE routing.
SUITE_TO_FAMILY = {
    "gsm8k": "math",
    "humaneval": "swe",
    "swe_micro": "swe",
    "mmlu": "multihop",  # mostly factual entity recall
    "hellaswag": "multihop",
    "longctx_qa": "research",  # quoted findings, citations
    "folio": "logical",
    "proofwriter": "logical",
    "logiqa": "logical",
    "bigbench": "operational",  # varied; default
    "mtbench": "operational",
}


# Module-level MoE pipeline singleton (shared across all items in a run).
_moe_pipeline_singleton = MoEPipeline(
    model_backend=None,
    memory_persistence_path="",
    quality_floor=0.98,
)


def _get_task_family(suite: str) -> str:
    """Map suite name to expert family."""
    return SUITE_TO_FAMILY.get(suite, "operational")


def _maybe_sample_long_context_with_moe(item: SuiteItem) -> tuple[str, dict | None]:
    """If the item has candidate chunks, route to MoE expert and sample top-K.

    The MoE expert injects domain-specific anchors before sampling (e.g.,
    (Author, Year) citations in research, variable names in code).

    Returns (effective_task_text, sampling_info). sampling_info is None if no
    sampling was applied.
    """
    if not item.context_chunks or not item.short_task or not item.chunks_target_keep:
        return item.task_text, None

    family = _get_task_family(item.suite)
    chunks = list(item.context_chunks)
    budget = max(1, min(item.chunks_target_keep, len(chunks)))

    try:
        result = _moe_pipeline_singleton.process_task(
            task_text=item.short_task,
            incoming_messages=[],
            prior_context=chunks,
            task_family=family,
            must_keep_facts=None,
        )
    except Exception:
        # If MoE fails for any reason, fall through to raw task.
        return item.task_text, None

    # Recover the sampled/pruned chunks from the expert's debug output.
    # The expert may have injected anchors and sampled; we use either
    # inline_chunks or pruned_context to build the effective task.
    inline = result.debug.get("inline_chunks", [])
    pruned = result.debug.get("pruned_context", [])
    kept = [c for c in (inline or pruned or []) if c]

    if not kept or len(kept) == 0:
        return item.task_text, None

    body = ["Read the following passages and answer the question."]
    body.append("")
    body.append("PASSAGES:")
    body.extend(kept)
    body.append("")
    body.append(item.short_task)
    new_task_text = "\n".join(body)

    return new_task_text, {
        "kept_count": len(kept),
        "total_count": len(chunks),
        "budget": budget,
        "expert_id": result.debug.get("expert_id"),
        "quality_proxy": result.debug.get("quality_proxy"),
    }


def _moe_compact_reasoning(reasoning_texts: list[str], family: str, task_text: str) -> list[str]:
    """Pass worker reasoning through MoE expert's compression."""
    if not reasoning_texts or not any(reasoning_texts):
        return reasoning_texts
    # Math reasoning chains are dense — anchors keep numerals, but compression
    # still strips operator/equation glue between them, so the synthesizer can't
    # reconstruct the chain. Bypass compression for math; rely on sampling alone.
    if family == "math":
        return reasoning_texts

    try:
        result = _moe_pipeline_singleton.process_task(
            task_text=task_text,
            incoming_messages=reasoning_texts,
            prior_context=[],
            task_family=family,
        )
    except Exception:
        # If MoE fails, return original reasoning.
        return reasoning_texts

    compressed = result.debug.get("compressed_messages", reasoning_texts)
    # Validate shape: must be a list with same length as input.
    if not isinstance(compressed, list) or len(compressed) != len(reasoning_texts):
        return reasoning_texts
    return compressed


def _run_worker(worker_id: int, subtask_prompt: str) -> tuple[CallLog, dict | None]:
    prompt = WORKER_TEMPLATE.format(worker_id=worker_id, subtask_prompt=subtask_prompt)
    result = _client_for(WORKER_PROVIDER).call(
        model=WORKER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=WORKER_MAX_TOKENS,
    )
    obj, parse_err = parse_json_object(result.text)
    log = usage_to_calllog(
        role=f"worker.{worker_id}",
        prompt=prompt,
        response_text=result.text,
        usage=result.usage,
        parse_error=parse_err,
    )
    return log, obj


def _coerce_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    return json.dumps(x, ensure_ascii=False)


def run(item: SuiteItem) -> PipelineRun:
    pr = PipelineRun(
        item_id=item.item_id,
        suite=item.suite,
        shape=SHAPE,
        variant=VARIANT,
        final_answer="",
        parse_error=None,
    )

    task_family = _get_task_family(item.suite)

    # 0) MoE-based long-context sampling if applicable.
    effective_task_text, sampling_info = _maybe_sample_long_context_with_moe(item)

    # 1) Decompose (identical to baseline, possibly trimmed input)
    decompose_prompt = DECOMPOSE_TEMPLATE.format(
        suite_type=item.suite_type,
        answer_format=item.answer_format,
        task_text=effective_task_text,
    )
    decompose_result = _client_for(SUPERVISOR_PROVIDER).call(
        model=SUPERVISOR_MODEL,
        messages=[{"role": "user", "content": decompose_prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=DECOMPOSE_MAX_TOKENS,
    )
    decompose_obj, decompose_err = parse_json_object(decompose_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="supervisor.decompose",
            prompt=decompose_prompt,
            response_text=decompose_result.text,
            usage=decompose_result.usage,
            parse_error=decompose_err,
        )
    )
    if decompose_obj is None:
        pr.parse_error = f"decompose: {decompose_err}"
        return pr

    subtasks = decompose_obj.get("subtasks") or []
    synthesis_strategy = decompose_obj.get("synthesis_strategy") or "(no strategy provided)"
    if not isinstance(subtasks, list) or len(subtasks) != 3:
        subtasks = [{"id": i + 1, "prompt": effective_task_text} for i in range(3)]
        synthesis_strategy = "(decomposition malformed — workers re-solved umbrella task)"

    # 2) Workers in parallel (identical to baseline)
    worker_prompts = [
        (st.get("id", i + 1), st.get("prompt", item.task_text))
        for i, st in enumerate(subtasks[:3])
    ]
    worker_outputs: list[dict | None] = [None, None, None]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(_run_worker, wid, prompt): idx
            for idx, (wid, prompt) in enumerate(worker_prompts)
        }
        for fut in concurrent.futures.as_completed(futures):
            idx = futures[fut]
            log, obj = fut.result()
            pr.calls.append(log)
            worker_outputs[idx] = obj

    # Reorder calls so worker logs are id-ordered between decompose and synthesize.
    decompose_log = pr.calls[0]
    worker_logs = sorted(
        [c for c in pr.calls if c.role.startswith("worker.")],
        key=lambda c: c.role,
    )
    pr.calls = [decompose_log] + worker_logs

    # 3) Synthesize — using OPTIMIZED prompt with MoE-compressed reasoning
    answers = [
        _coerce_str(w.get("answer") if w else "")
        for w in worker_outputs
    ]
    reasonings_raw = [
        _coerce_str(w.get("reasoning") if w else "")
        for w in worker_outputs
    ]
    confidences = [
        (w.get("confidence") if w and isinstance(w.get("confidence"), (int, float)) else 0.0)
        for w in worker_outputs
    ]
    reasonings_compact = _moe_compact_reasoning(reasonings_raw, task_family, effective_task_text)

    def _w_json(obj: dict | None) -> str:
        if obj is None:
            return json.dumps({"answer": "", "reasoning": "(unparseable)", "confidence": 0.0})
        return json.dumps(obj)

    if task_family == "math":
        # Math regressed -26.7pp on gsm8k with the lean synth template — the
        # rules preamble carries instructions the synthesizer relies on to
        # combine numerical worker outputs. Use the baseline template so the
        # synthesizer sees full structure.
        synth_prompt_optimized = BASELINE_SYNTHESIZE_TEMPLATE.format(
            task_text=effective_task_text,
            answer_format=item.answer_format,
            synthesis_strategy=synthesis_strategy,
            worker_1_json=_w_json(worker_outputs[0]),
            worker_2_json=_w_json(worker_outputs[1]),
            worker_3_json=_w_json(worker_outputs[2]),
        )
    else:
        synth_prompt_optimized = OPTIMIZED_SYNTHESIZE_TEMPLATE.format(
            task_text=effective_task_text,
            answer_format=item.answer_format,
            w1_answer=answers[0],
            w1_reasoning=reasonings_compact[0],
            w1_conf=confidences[0],
            w2_answer=answers[1],
            w2_reasoning=reasonings_compact[1],
            w2_conf=confidences[1],
            w3_answer=answers[2],
            w3_reasoning=reasonings_compact[2],
            w3_conf=confidences[2],
        )

    synth_result = _client_for(SUPERVISOR_PROVIDER).call(
        model=SUPERVISOR_MODEL,
        messages=[{"role": "user", "content": synth_prompt_optimized}],
        temperature=0.0,
        seed=42,
        max_tokens=SYNTHESIZE_MAX_TOKENS,
    )
    synth_obj, synth_err = parse_json_object(synth_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="supervisor.synthesize",
            prompt=synth_prompt_optimized,
            response_text=synth_result.text,
            usage=synth_result.usage,
            parse_error=synth_err,
        )
    )

    # Quality-floor rollback: if the lean prompt failed to parse,
    # rerun with the baseline synthesis prompt on the same worker outputs.
    if synth_obj is None:
        rollback_prompt = BASELINE_SYNTHESIZE_TEMPLATE.format(
            task_text=effective_task_text,
            answer_format=item.answer_format,
            synthesis_strategy=synthesis_strategy,
            worker_1_json=_w_json(worker_outputs[0]),
            worker_2_json=_w_json(worker_outputs[1]),
            worker_3_json=_w_json(worker_outputs[2]),
        )
        rollback_result = _client_for(SUPERVISOR_PROVIDER).call(
            model=SUPERVISOR_MODEL,
            messages=[{"role": "user", "content": rollback_prompt}],
            temperature=0.0,
            seed=42,
            max_tokens=SYNTHESIZE_MAX_TOKENS,
        )
        rollback_obj, rollback_err = parse_json_object(rollback_result.text)
        pr.calls.append(
            usage_to_calllog(
                role="supervisor.synthesize.rollback",
                prompt=rollback_prompt,
                response_text=rollback_result.text,
                usage=rollback_result.usage,
                parse_error=rollback_err,
            )
        )
        synth_obj = rollback_obj
        if synth_obj is None:
            pr.parse_error = f"synthesize: {synth_err}; rollback: {rollback_err}"
            pr.final_answer = rollback_result.text.strip()
            return pr

    final = synth_obj.get("final_answer")
    if not isinstance(final, str):
        final = "" if final is None else str(final)
    pr.final_answer = final
    return pr
