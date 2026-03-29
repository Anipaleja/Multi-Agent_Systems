"""Adaptive Semantic Sampler Implementation"""

import math
from typing import List, Dict, Tuple, Set
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class SamplingMetrics:
    """Metrics for sampling decision"""
    relevance_score: float
    importance_score: float
    frequency_score: float
    recency_score: float
    combined_score: float


class AdaptiveSemanticSampler:
    """
    Intelligently samples critical contexts to maximize information retention
    while minimizing token usage.
    
    Uses multi-modal scoring:
    - Semantic relevance (TF-IDF style scoring)
    - Entity frequency (how often concepts appear)
    - Temporal recency (weighted by position in history)
    - Information entropy (how much unique information)
    """
    
    def __init__(self, 
                 budget: int = 5,
                 relevance_weight: float = 0.35,
                 frequency_weight: float = 0.25,
                 recency_weight: float = 0.20,
                 entropy_weight: float = 0.20):
        self.budget = budget
        self.relevance_weight = relevance_weight
        self.frequency_weight = frequency_weight
        self.recency_weight = recency_weight
        self.entropy_weight = entropy_weight
        
        # Vocabularies for semantic understanding
        self.task_keywords: Set[str] = set()
        self.entity_index: Dict[str, List[int]] = defaultdict(list)
        self.concept_frequency: Counter = Counter()
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract important keywords from text"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
            'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        words = text.lower().split()
        keywords = {w for w in words 
                   if len(w) > 3 and w not in stop_words and w.isalpha()}
        return keywords
    
    def _calculate_relevance(self, context: str, task_text: str) -> float:
        """Calculate semantic relevance to task"""
        task_keywords = self._extract_keywords(task_text)
        context_keywords = self._extract_keywords(context)
        
        if not task_keywords:
            return 0.0
        
        # Jaccard similarity
        intersection = len(task_keywords & context_keywords)
        union = len(task_keywords | context_keywords)
        
        if union == 0:
            return 0.0
        
        relevance = intersection / union
        
        # Boost for exact phrase matches
        task_text_lower = task_text.lower()
        for keyword in context_keywords:
            if keyword in task_text_lower:
                relevance = min(1.0, relevance + 0.1)
        
        return min(1.0, relevance)
    
    def _calculate_frequency_score(self, context: str, 
                                  all_contexts: List[str]) -> float:
        """Score based on entity/concept frequency"""
        keywords = self._extract_keywords(context)
        
        if not keywords:
            return 0.0
        
        # Count keyword occurrences across all contexts
        total_occurrences = 0
        for keyword in keywords:
            for other_context in all_contexts:
                if keyword in other_context.lower():
                    total_occurrences += 1
        
        # Normalize: frequent concepts are important
        avg_frequency = total_occurrences / len(keywords) if keywords else 0
        freq_score = min(1.0, avg_frequency / len(all_contexts))
        
        return freq_score
    
    def _calculate_recency_score(self, index: int, total_contexts: int) -> float:
        """Score based on position recency (recently mentioned contexts are more relevant)"""
        if total_contexts == 0:
            return 0.0
        
        # Exponential decay: recent contexts score higher
        position_ratio = index / total_contexts
        recency = math.exp(-2.0 * (1.0 - position_ratio))
        
        return min(1.0, recency)
    
    def _calculate_entropy(self, context: str, 
                          other_contexts: List[str]) -> float:
        """Calculate information entropy - unique information content"""
        keywords = self._extract_keywords(context)
        
        if not keywords:
            return 0.0
        
        # Count how many keywords are unique to this context
        all_other_keywords = set()
        for other in other_contexts:
            all_other_keywords.update(self._extract_keywords(other))
        
        unique_keywords = keywords - all_other_keywords
        uniqueness = len(unique_keywords) / len(keywords) if keywords else 0
        
        # Also score by context length (more information)
        length_score = min(1.0, len(context.split()) / 50.0)
        
        entropy = 0.6 * uniqueness + 0.4 * length_score
        return min(1.0, entropy)
    
    def score_contexts(self, 
                      contexts: List[str],
                      task_text: str) -> List[Tuple[int, float, SamplingMetrics]]:
        """
        Score all contexts and return indexed scores
        
        Returns: List of (index, combined_score, metrics) tuples
        """
        scores = []
        
        for idx, context in enumerate(contexts):
            relevance = self._calculate_relevance(context, task_text)
            frequency = self._calculate_frequency_score(context, contexts)
            recency = self._calculate_recency_score(idx, len(contexts))
            
            # Entropy calculated against all other contexts
            other_contexts = contexts[:idx] + contexts[idx+1:]
            entropy = self._calculate_entropy(context, other_contexts)
            
            # Combined weighted score
            combined = (
                self.relevance_weight * relevance +
                self.frequency_weight * frequency +
                self.recency_weight * recency +
                self.entropy_weight * entropy
            )
            
            metrics = SamplingMetrics(
                relevance_score=relevance,
                importance_score=frequency,
                frequency_score=frequency,
                recency_score=recency,
                combined_score=combined
            )
            
            scores.append((idx, combined, metrics))
        
        return scores
    
    def sample(self, 
              contexts: List[str],
              task_text: str,
              adaptive_budget: int = None) -> Tuple[List[str], Dict[str, any]]:
        """
        Adaptively sample the most important contexts
        
        Args:
            contexts: List of context strings
            task_text: The current task
            adaptive_budget: Override default budget based on complexity
        
        Returns:
            (sampled_contexts, debug_info)
        """
        if not contexts:
            return [], {"sampled_count": 0, "total_count": 0}
        
        budget = adaptive_budget or self.budget
        budget = max(1, min(budget, len(contexts)))
        
        # Score all contexts
        scores = self.score_contexts(contexts, task_text)
        
        # Sort by combined score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select top-budget contexts, but preserve some order
        sampled_indices = sorted([scores[i][0] for i in range(budget)])
        sampled_contexts = [contexts[i] for i in sampled_indices]
        
        # Debug info
        debug_info = {
            "sampled_count": len(sampled_contexts),
            "total_count": len(contexts),
            "budget": budget,
            "average_relevance": sum(s[2].relevance_score for s in scores[:budget]) / budget,
            "average_importance": sum(s[2].importance_score for s in scores[:budget]) / budget,
            "average_recency": sum(s[2].recency_score for s in scores[:budget]) / budget,
            "average_entropy": sum(s[2].combined_score for s in scores[:budget]) / budget,
            "top_3_scores": [scores[i][1] for i in range(min(3, len(scores)))],
        }
        
        return sampled_contexts, debug_info
    
    def sample_with_fallback(self,
                            contexts: List[str],
                            task_text: str,
                            token_budget: int = 100,
                            avg_tokens_per_context: int = 20) -> List[str]:
        """
        Sample contexts while respecting a token budget
        Adapts sampling based on available tokens
        """
        if not contexts:
            return []
        
        # Calculate adaptive budget based on token constraints
        tokens_available = token_budget
        max_contexts = tokens_available // avg_tokens_per_context
        adaptive_budget = max(1, min(max_contexts, len(contexts)))
        
        sampled, _ = self.sample(contexts, task_text, adaptive_budget=adaptive_budget)
        return sampled
