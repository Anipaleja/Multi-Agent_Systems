"""Local-only backend for the token efficiency test app.

This backend does not call external APIs or require API keys. It uses the
token_efficiency_model pipeline in the repo to optimize the prompts, then
calls local Ollama models for the actual agent outputs.
"""

import os
import sys
import json
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
TOKEN_MODEL_ROOT = WORKSPACE_ROOT / "token_efficiency_model"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from token_efficiency_model.combined_tactics import TokenEfficientPipeline, MoEPipeline
from token_efficiency_model.common.metrics import estimate_tokens

app = Flask(__name__)
CORS(app)

# Local optimization pipeline from token_efficiency_model.
pipeline = MoEPipeline(quality_floor=0.98)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
# Installed local Ollama tags from `ollama list`.
# We prefer the lighter/faster local models to keep the three-agent demo responsive.
OLLAMA_MODELS = ["deepseek-r1:8b", "qwen2.5:7b", "qwen3.5:latest"] #CHANGE TO YOUR LOCAL MODELS IF DIFFERENT!!


def _prewarm_ollama() -> None:
    request_body = {
        "model": OLLAMA_MODELS[0],
        "stream": False,
        "messages": [{"role": "user", "content": "Warm up."}],
        "options": {"num_predict": 1, "num_ctx": 256},
        "keep_alive": "10m",
    }
    request_data = json.dumps(request_body).encode("utf-8")
    request_obj = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=60) as response:
            response.read()
    except Exception:
        pass


def _build_agent_prompt(agent_name: str, task_text: str, prior_outputs: list[str]) -> str:
    if agent_name == "Architect":
        return (
            f"Task: {task_text}\n\n"
            "You are the Architect agent. Break this task into a clear structural plan with 3-4 components. Be concise."
        )

    if agent_name == "Builder":
        architect_output = prior_outputs[0] if prior_outputs else ""
        return (
            f"Task: {task_text}\n\n[ARCHITECT PLAN]\n{architect_output}\n[/ARCHITECT PLAN]\n\n"
            "You are the Builder agent. Execute the plan above. Build out the core content."
        )

    architect_output = prior_outputs[0] if prior_outputs else ""
    builder_output = prior_outputs[1] if len(prior_outputs) > 1 else ""
    return (
        f"Task: {task_text}\n\n[ARCHITECT PLAN]\n{architect_output}\n[/ARCHITECT PLAN]\n\n"
        f"[BUILDER OUTPUT]\n{builder_output}\n[/BUILDER OUTPUT]\n\n"
        "You are the Reviewer agent. Review both outputs, fill gaps, and write the final polished result."
    )


def _run_local_agent(
    agent_id: int,
    agent_name: str,
    task_text: str,
    prior_outputs: list[str],
    complexity: float,
    urgency: float,
    ollama_model: str,
):
    prompt = _build_agent_prompt(agent_name, task_text, prior_outputs)

    if agent_id == 1:
        incoming_messages = []
        prior_context = []
    elif agent_id == 2:
        incoming_messages = prior_outputs[:1]
        prior_context = prior_outputs[:1]
    else:
        incoming_messages = prior_outputs[:2]
        prior_context = prior_outputs[:2]

    result = pipeline.process_task(
        task_text=prompt,
        incoming_messages=incoming_messages,
        prior_context=prior_context,
        task_id=f"local-agent-{agent_id}",
        complexity=complexity,
        urgency=urgency,
        compression_level=2,
        prune_budget=5,
        protocol_mode="compact",
    )

    request_body = {
        "model": ollama_model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are part of a local multi-agent test harness. "
                    "Answer clearly and concisely."
                ),
            },
            {
                "role": "user",
                "content": result.protocol_payload,
            },
        ],
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": 96,
            "num_ctx": 1024,
        },
        "keep_alive": "10m",
    }

    request_data = json.dumps(request_body).encode("utf-8")
    request_url = f"{OLLAMA_BASE_URL}/api/chat"
    request_obj = urllib.request.Request(
        request_url,
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=180) as response:
            ollama_response = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Ollama is not reachable at {OLLAMA_BASE_URL}. Start it with `ollama serve` and make sure models {', '.join(OLLAMA_MODELS)} are available."
        ) from error

    model_output = ollama_response.get("message", {}).get("content", "")
    prompt_eval_count = int(ollama_response.get("prompt_eval_count", estimate_tokens(result.protocol_payload)))
    eval_count = int(ollama_response.get("eval_count", estimate_tokens(model_output)))

    return {
        "id": agent_id,
        "name": agent_name,
        "provider": "ollama",
        "model": ollama_model,
        "status": "done",
        "output": model_output,
        "output_tokens": eval_count,
        "usage": {
            "input_tokens": prompt_eval_count,
            "output_tokens": eval_count,
            "total_tokens": prompt_eval_count + eval_count,
        },
        "pipeline": {
            "baseline_tokens": result.baseline_tokens,
            "optimized_tokens": result.optimized_tokens,
            "steady_state_tokens": result.steady_state_tokens,
            "savings_pct": result.savings_pct,
            "quality_proxy": result.quality_proxy,
            "routed_model": ollama_model,
            "debug": result.debug,
            "ollama": {
                "base_url": OLLAMA_BASE_URL,
                "prompt_eval_count": prompt_eval_count,
                "eval_count": eval_count,
            },
        },
    }


def _fetch_installed_ollama_models() -> list[str]:
    request_obj = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/tags",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request_obj, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    models = [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
    return models


def _calculate_token_stats(agent_results: list[dict]):
    agent1 = agent_results[0]["usage"]
    agent2 = agent_results[1]["usage"]
    agent3 = agent_results[2]["usage"]

    agent2_redundant_tokens = agent1["output_tokens"]
    agent3_redundant_tokens = agent1["output_tokens"] + agent2["output_tokens"]
    total_redundant_tokens = agent2_redundant_tokens + agent3_redundant_tokens

    total_tokens = (
        agent1["input_tokens"] + agent1["output_tokens"]
        + agent2["input_tokens"] + agent2["output_tokens"]
        + agent3["input_tokens"] + agent3["output_tokens"]
    )

    unique_tokens = total_tokens - total_redundant_tokens
    efficiency_score = round((unique_tokens / total_tokens) * 100) if total_tokens > 0 else 0

    return {
        "totalTokens": total_tokens,
        "uniqueTokens": unique_tokens,
        "redundantTokens": total_redundant_tokens,
        "efficiencyScore": efficiency_score,
        "totalPromptTokens": agent1["input_tokens"] + agent2["input_tokens"] + agent3["input_tokens"],
        "totalCompletionTokens": agent1["output_tokens"] + agent2["output_tokens"] + agent3["output_tokens"],
        "agent2RedundantTokens": agent2_redundant_tokens,
        "agent3RedundantTokens": agent3_redundant_tokens,
    }


@app.route('/api/run-agents', methods=['POST'])
def run_agents_local():
    """Run the three-agent chain locally with the token-efficiency pipeline."""
    try:
        data = request.json or {}
        task_text = data.get('task_text', '')
        complexity = float(data.get('complexity', 0.55))
        urgency = float(data.get('urgency', 0.5))
        selected_models = data.get('selected_models', OLLAMA_MODELS)

        if not isinstance(selected_models, list) or len(selected_models) != 3:
            selected_models = OLLAMA_MODELS

        agent1 = _run_local_agent(1, 'Architect', task_text, [], complexity, urgency, selected_models[0])
        agent2 = _run_local_agent(2, 'Builder', task_text, [agent1['output']], complexity, urgency, selected_models[1])
        agent3 = _run_local_agent(3, 'Reviewer', task_text, [agent1['output'], agent2['output']], complexity, urgency, selected_models[2])

        agent_results = [agent1, agent2, agent3]
        token_stats = _calculate_token_stats(agent_results)

        return jsonify({
            'success': True,
            'local_only': True,
            'agents': agent_results,
            'tokenStats': token_stats,
            'pipelineNotes': {
                'source': 'token_efficiency_model',
                'routerModels': selected_models,
                'apiKeysRequired': False,
                'runtime': 'ollama',
            },
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/models', methods=['GET'])
def list_models():
    """Return installed local Ollama models for UI dropdowns."""
    try:
        models = _fetch_installed_ollama_models()
        return jsonify({
            'success': True,
            'models': models,
            'defaultModels': OLLAMA_MODELS,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'models': OLLAMA_MODELS,
            'defaultModels': OLLAMA_MODELS,
            'error': str(e),
        }), 200


@app.route('/api/optimize', methods=['POST'])
def optimize_context():
    """
    Optimize a task's context and return token comparison

    Request body:
    {
        "task_text": "The main task...",
        "incoming_messages": ["msg1", "msg2", ...],
        "prior_context": ["ctx1", "ctx2", ...],
        "complexity": 0.5,
        "urgency": 0.5,
        "must_keep_facts": ["fact1", "fact2"],  # optional (MoE)
        "task_family": "math",                   # optional (MoE)
        "scenario_type": "planning"              # optional (MoE)
    }

    Response:
    {
        "baseline_tokens": 1024,
        "optimized_tokens": 768,
        "savings_pct": 25.0,
        "quality_proxy": 0.99,
        "compressed_payload": "...",
        "debug": {..., "expert_id": "math", "must_keep_recall": 0.95}
    }
    """
    try:
        data = request.json

        task_text = data.get('task_text', '')
        incoming_messages = data.get('incoming_messages', [])
        prior_context = data.get('prior_context', [])
        complexity = data.get('complexity', 0.5)
        urgency = data.get('urgency', 0.5)
        must_keep_facts = data.get('must_keep_facts')
        task_family = data.get('task_family')
        scenario_type = data.get('scenario_type')

        # Run through optimization pipeline
        result = pipeline.process_task(
            task_text=task_text,
            incoming_messages=incoming_messages,
            prior_context=prior_context,
            must_keep_facts=must_keep_facts,
            task_family=task_family,
            scenario_type=scenario_type,
            task_id="api-request",
            complexity=complexity,
            urgency=urgency,
            compression_level=2,
            prune_budget=5,
            protocol_mode="compact",
        )

        debug_output = {
            "compression_stats": result.debug.get("compression", {}),
            "sampling_stats": result.debug.get("adaptive_sampling", {}),
            "cache_hit_rate": result.debug.get("cache_hit_rate", 0),
            "rehydration_events": result.debug.get("rehydration_events", 0),
        }

        # Add MoE-specific fields if available
        if "expert_id" in result.debug:
            debug_output["expert_id"] = result.debug.get("expert_id")
        if "must_keep_recall" in result.debug:
            debug_output["must_keep_recall"] = result.debug.get("must_keep_recall")

        return jsonify({
            "success": True,
            "baseline_tokens": result.baseline_tokens,
            "optimized_tokens": result.optimized_tokens,
            "steady_state_tokens": result.steady_state_tokens,
            "savings_pct": result.savings_pct,
            "quality_proxy": result.quality_proxy,
            "routed_model": result.routed_model,
            "compressed_payload": result.protocol_payload[:200] + "..." if len(result.protocol_payload) > 200 else result.protocol_payload,
            "debug": debug_output
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/estimate-tokens', methods=['POST'])
def estimate_tokens_endpoint():
    """
    Quick token estimation without optimization
    """
    try:
        data = request.json
        text = data.get('text', '')
        tokens = estimate_tokens(text)
        
        return jsonify({
            "success": True,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "tokens": tokens
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "token-efficiency-local-backend",
        "status": "ready",
        "modelRoot": str(TOKEN_MODEL_ROOT),
    })


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return ('', 204)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    _prewarm_ollama()
    print(f"\n✓ Token Efficiency Backend Ready")
    print(f"  Token model path: {TOKEN_MODEL_ROOT}")
    print(f"  Ollama base URL: {OLLAMA_BASE_URL}")
    print(f"  Models: {', '.join(OLLAMA_MODELS)}")
    print(f"  NO API KEYS REQUIRED - local optimization only")
    print(f"  Starting on http://localhost:{port}\n")
    app.run(debug=True, port=port, use_reloader=False)
