"""4-agent debate pipeline organized as 2 sequential pairs, Mixture-of-Experts variant.

Same shape as `debate2x2_baseline` and `debate2x2_optimized`.
Same model bindings and task interface.

Where the MoE layer engages:
1. Suite → expert routing: Based on the suite name (gsm8k, humaneval, etc.),
   route to a specialized expert family (math, swe, research, etc.).
2. Long-context sampling: If the item carries context chunks, the MoEPipeline
   injects expert-aware anchors before sampling, preserving domain-critical
   facts (e.g., citations in research, variable names in code).
3. Round-1 compression: The proposer and critic outputs are compressed through
   the MoEPipeline before being passed to the reviser and judge, preserving
   critical facts and domain-specific identifiers.

Same quality-floor discipline as optimized: fallback to baseline judge
prompt if the lean prompt fails to parse.
"""

from __future__ import annotations

import json

from eval.providers import deepseek_client, groq_client, openai_client
from eval.suites import SuiteItem
from token_efficiency_model.combined_tactics.moe_pipeline import MoEPipeline

from .shape import CallLog, PipelineRun, parse_json_object, usage_to_calllog
from .debate2x2_baseline import (
    PROPOSE_TEMPLATE,
    CRITIQUE_TEMPLATE,
    REVISE_TEMPLATE,
    JUDGE_TEMPLATE as BASELINE_JUDGE_TEMPLATE,
    JUDGE_CRITIC_MODEL,
    JUDGE_CRITIC_PROVIDER,
    PROPOSER_REVISER_MODEL,
    PROPOSER_REVISER_PROVIDER,
    PROPOSE_MAX_TOKENS,
    CRITIQUE_MAX_TOKENS,
    REVISE_MAX_TOKENS,
    JUDGE_MAX_TOKENS,
    _client_for,
    _coerce_str,
    _json_payload,
)
from .debate2x2_optimized import OPTIMIZED_JUDGE_TEMPLATE


SHAPE = "debate2x2"
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


def _moe_compact_text(text: str, family: str, task_text: str) -> str:
    """Pass a single text through MoE expert's compression."""
    if not text:
        return text
    # Math reasoning chains are dense — anchors keep numerals, but compression
    # still strips operator/equation glue between them. Bypass for math.
    if family == "math":
        return text

    try:
        result = _moe_pipeline_singleton.process_task(
            task_text=task_text,
            incoming_messages=[text],
            prior_context=[],
            task_family=family,
        )
    except Exception:
        # If MoE fails, return original text.
        return text

    compressed = result.debug.get("compressed_messages", [text])
    # Validate shape: must be a list with at least one element.
    if not isinstance(compressed, list) or len(compressed) == 0:
        return text
    return compressed[0]


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

    # 1) Propose
    propose_prompt = PROPOSE_TEMPLATE.format(
        suite_type=item.suite_type,
        answer_format=item.answer_format,
        task_text=effective_task_text,
    )
    propose_result = _client_for(PROPOSER_REVISER_PROVIDER).call(
        model=PROPOSER_REVISER_MODEL,
        messages=[{"role": "user", "content": propose_prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=PROPOSE_MAX_TOKENS,
    )
    propose_obj, propose_err = parse_json_object(propose_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="proposer",
            prompt=propose_prompt,
            response_text=propose_result.text,
            usage=propose_result.usage,
            parse_error=propose_err,
        )
    )

    proposer_payload = _json_payload(
        propose_obj,
        {"answer": "", "reasoning": "(proposer unparseable)", "confidence": 0.0},
    )

    # 2) Critique
    critique_prompt = CRITIQUE_TEMPLATE.format(
        task_text=effective_task_text,
        answer_format=item.answer_format,
        proposer_json=proposer_payload,
    )
    critique_result = _client_for(JUDGE_CRITIC_PROVIDER).call(
        model=JUDGE_CRITIC_MODEL,
        messages=[{"role": "user", "content": critique_prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=CRITIQUE_MAX_TOKENS,
    )
    critique_obj, critique_err = parse_json_object(critique_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="critic",
            prompt=critique_prompt,
            response_text=critique_result.text,
            usage=critique_result.usage,
            parse_error=critique_err,
        )
    )

    # Compress critic objections and fixes for the reviser.
    if critique_obj:
        c_objs_raw = critique_obj.get("objections") or []
        if isinstance(c_objs_raw, list):
            c_objections_str = "; ".join(_coerce_str(x) for x in c_objs_raw)
        else:
            c_objections_str = _coerce_str(c_objs_raw)
        c_objections_compressed = _moe_compact_text(c_objections_str, task_family, effective_task_text)

        c_fixes_raw = _coerce_str(critique_obj.get("suggested_fixes") or "")
        c_fixes_compressed = _moe_compact_text(c_fixes_raw, task_family, effective_task_text)

        # Rebuild compressed critic object
        critique_obj_compressed = {
            "objections": c_objections_compressed.split("; ") if c_objections_compressed else [],
            "severity": critique_obj.get("severity") or "none",
            "suggested_fixes": c_fixes_compressed,
        }
    else:
        critique_obj_compressed = {
            "objections": [],
            "severity": "none",
            "suggested_fixes": "(critic unparseable)",
        }

    critic_payload = _json_payload(
        critique_obj_compressed,
        {"objections": [], "severity": "none", "suggested_fixes": "(critic unparseable)"},
    )

    # 3) Revise
    revise_prompt = REVISE_TEMPLATE.format(
        task_text=effective_task_text,
        answer_format=item.answer_format,
        proposer_json=proposer_payload,
        critic_json=critic_payload,
    )
    revise_result = _client_for(PROPOSER_REVISER_PROVIDER).call(
        model=PROPOSER_REVISER_MODEL,
        messages=[{"role": "user", "content": revise_prompt}],
        temperature=0.0,
        seed=42,
        max_tokens=REVISE_MAX_TOKENS,
    )
    revise_obj, revise_err = parse_json_object(revise_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="reviser",
            prompt=revise_prompt,
            response_text=revise_result.text,
            usage=revise_result.usage,
            parse_error=revise_err,
        )
    )

    reviser_payload = _json_payload(
        revise_obj,
        {"revised_answer": "", "revised_reasoning": "(reviser unparseable)",
         "addressed_objections": [], "confidence": 0.0},
    )

    # 4) Judge — using OPTIMIZED prompt with MoE-compressed reasoning fields
    p_answer = _coerce_str(propose_obj.get("answer") if propose_obj else "")
    p_reasoning_raw = _coerce_str(propose_obj.get("reasoning") if propose_obj else "")
    p_conf_v = propose_obj.get("confidence") if propose_obj else 0.0
    p_conf = float(p_conf_v) if isinstance(p_conf_v, (int, float)) else 0.0
    p_reasoning = _moe_compact_text(p_reasoning_raw, task_family, effective_task_text) or p_reasoning_raw

    if critique_obj:
        c_severity = _coerce_str(critique_obj.get("severity") or "none")
        c_objs_raw = critique_obj.get("objections") or []
        if isinstance(c_objs_raw, list):
            c_objections_raw = "; ".join(_coerce_str(x) for x in c_objs_raw)
        else:
            c_objections_raw = _coerce_str(c_objs_raw)
        c_fixes_raw = _coerce_str(critique_obj.get("suggested_fixes") or "")
    else:
        c_severity = "none"
        c_objections_raw = ""
        c_fixes_raw = "(critic unparseable)"
    c_objections = _moe_compact_text(c_objections_raw, task_family, effective_task_text) or c_objections_raw
    c_fixes = _moe_compact_text(c_fixes_raw, task_family, effective_task_text) or c_fixes_raw

    if revise_obj:
        r_answer = _coerce_str(revise_obj.get("revised_answer") or "")
        r_reasoning_raw = _coerce_str(revise_obj.get("revised_reasoning") or "")
        r_addressed_raw = revise_obj.get("addressed_objections") or []
        if isinstance(r_addressed_raw, list):
            r_addressed_raw = "; ".join(_coerce_str(x) for x in r_addressed_raw)
        else:
            r_addressed_raw = _coerce_str(r_addressed_raw)
        r_conf_v = revise_obj.get("confidence")
        r_conf = float(r_conf_v) if isinstance(r_conf_v, (int, float)) else 0.0
    else:
        r_answer = ""
        r_reasoning_raw = "(reviser unparseable)"
        r_addressed_raw = ""
        r_conf = 0.0
    r_reasoning = _moe_compact_text(r_reasoning_raw, task_family, effective_task_text) or r_reasoning_raw
    r_addressed = _moe_compact_text(r_addressed_raw, task_family, effective_task_text) or r_addressed_raw

    judge_prompt_optimized = OPTIMIZED_JUDGE_TEMPLATE.format(
        task_text=effective_task_text,
        answer_format=item.answer_format,
        p_answer=p_answer,
        p_reasoning=p_reasoning,
        p_conf=p_conf,
        c_severity=c_severity,
        c_objections=c_objections,
        c_fixes=c_fixes,
        r_answer=r_answer,
        r_reasoning=r_reasoning,
        r_addressed=r_addressed,
        r_conf=r_conf,
    )
    judge_result = _client_for(JUDGE_CRITIC_PROVIDER).call(
        model=JUDGE_CRITIC_MODEL,
        messages=[{"role": "user", "content": judge_prompt_optimized}],
        temperature=0.0,
        seed=42,
        max_tokens=JUDGE_MAX_TOKENS,
    )
    judge_obj, judge_err = parse_json_object(judge_result.text)
    pr.calls.append(
        usage_to_calllog(
            role="judge",
            prompt=judge_prompt_optimized,
            response_text=judge_result.text,
            usage=judge_result.usage,
            parse_error=judge_err,
        )
    )

    # Quality-floor rollback: if the lean prompt failed to parse,
    # rerun with the baseline judge prompt on the same agent outputs.
    if judge_obj is None:
        reviser_payload = _json_payload(
            revise_obj,
            {"revised_answer": "", "revised_reasoning": "(unparseable)",
             "addressed_objections": [], "confidence": 0.0},
        )
        rollback_prompt = BASELINE_JUDGE_TEMPLATE.format(
            task_text=effective_task_text,
            answer_format=item.answer_format,
            proposer_json=proposer_payload,
            critic_json=critic_payload,
            reviser_json=reviser_payload,
        )
        rollback_result = _client_for(JUDGE_CRITIC_PROVIDER).call(
            model=JUDGE_CRITIC_MODEL,
            messages=[{"role": "user", "content": rollback_prompt}],
            temperature=0.0,
            seed=42,
            max_tokens=JUDGE_MAX_TOKENS,
        )
        rollback_obj, rollback_err = parse_json_object(rollback_result.text)
        pr.calls.append(
            usage_to_calllog(
                role="judge.rollback",
                prompt=rollback_prompt,
                response_text=rollback_result.text,
                usage=rollback_result.usage,
                parse_error=rollback_err,
            )
        )
        judge_obj = rollback_obj
        if judge_obj is None:
            pr.parse_error = f"judge: {judge_err}; rollback: {rollback_err}"
            if revise_obj is not None and isinstance(revise_obj.get("revised_answer"), str):
                pr.final_answer = revise_obj["revised_answer"]
            elif propose_obj is not None and isinstance(propose_obj.get("answer"), str):
                pr.final_answer = propose_obj["answer"]
            else:
                pr.final_answer = rollback_result.text.strip()
            return pr

    final = judge_obj.get("final_answer")
    if not isinstance(final, str):
        final = "" if final is None else str(final)
    pr.final_answer = final
    return pr
