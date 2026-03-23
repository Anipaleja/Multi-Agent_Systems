import hashlib
from typing import Dict, List, Tuple


class SharedMemoryLayer:
    def __init__(self):
        self._chunks: Dict[str, str] = {}

    def _chunk_id(self, text: str) -> str:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
        return f"mem:{digest}"

    def store(self, chunks: List[str]) -> List[str]:
        ids = []
        for chunk in chunks:
            chunk_id = self._chunk_id(chunk)
            self._chunks[chunk_id] = chunk
            ids.append(chunk_id)
        return ids

    def retrieve(self, chunk_ids: List[str]) -> List[str]:
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    def materialize_or_reference(self, chunks: List[str]) -> Tuple[List[str], List[str]]:
        references = []
        inline = []
        for chunk in chunks:
            chunk_id = self._chunk_id(chunk)
            if chunk_id in self._chunks:
                references.append(chunk_id)
            else:
                self._chunks[chunk_id] = chunk
                inline.append(chunk)
                references.append(chunk_id)
        return inline, references
