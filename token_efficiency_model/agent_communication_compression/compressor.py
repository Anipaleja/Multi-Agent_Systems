from dataclasses import dataclass
from typing import List, Tuple

from common.metrics import estimate_tokens_many
from common.utils import normalize_whitespace, split_sentences


@dataclass
class CompressionStats:
    original_tokens: int
    compressed_tokens: int
    removed_redundant_sentences: int


class CommunicationCompressor:
    def __init__(self, level: int = 1):
        self.level = max(1, min(level, 3))

    def compress_messages(self, messages: List[str]) -> Tuple[List[str], CompressionStats]:
        cleaned = [normalize_whitespace(msg) for msg in messages if msg and msg.strip()]
        original_tokens = estimate_tokens_many(cleaned)

        seen = set()
        output = []
        removed = 0
        for msg in cleaned:
            dedup_sentences = []
            for sentence in split_sentences(msg):
                signature = sentence.lower()
                if signature in seen:
                    removed += 1
                    continue
                seen.add(signature)
                dedup_sentences.append(sentence)

            if self.level >= 2:
                dedup_sentences = dedup_sentences[: max(1, len(dedup_sentences) // 2)]
            if self.level >= 3 and dedup_sentences:
                dedup_sentences = dedup_sentences[:1]

            merged = " ".join(dedup_sentences).strip()
            if merged:
                output.append(merged)

        compressed_tokens = estimate_tokens_many(output)
        stats = CompressionStats(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            removed_redundant_sentences=removed,
        )
        return output, stats
