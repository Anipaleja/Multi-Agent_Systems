import json
from typing import Any, Dict, List


class AgentProtocol:
    FIELD_MAP = {
        "task_id": "t",
        "model": "m",
        "summary": "s",
        "context_refs": "c",
        "instructions": "i",
        "priority": "p",
    }

    def encode(self, payload: Dict[str, Any], mode: str = "compact") -> str:
        if mode == "raw-json":
            return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

        compact = {}
        for key, value in payload.items():
            mapped = self.FIELD_MAP.get(key, key)
            compact[mapped] = value
        return json.dumps(compact, separators=(",", ":"), ensure_ascii=False)

    def decode(self, encoded: str) -> Dict[str, Any]:
        data = json.loads(encoded)
        reverse_map = {v: k for k, v in self.FIELD_MAP.items()}
        expanded = {}
        for key, value in data.items():
            expanded[reverse_map.get(key, key)] = value
        return expanded

    def build_payload(
        self,
        task_id: str,
        model: str,
        summary: str,
        context_refs: List[str],
        instructions: str,
        priority: float,
    ) -> Dict[str, Any]:
        return {
            "task_id": task_id,
            "model": model,
            "summary": summary,
            "context_refs": context_refs,
            "instructions": instructions,
            "priority": round(priority, 3),
        }
