"""Query classification module for detecting user intent from queries and files."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    RESUME_REVIEW = "resume_review"
    MEETING_PREP = "meeting_prep"
    CONTRACT_REVIEW = "contract_review"
    DOCUMENT_ANALYSIS = "document_analysis"
    COMPARISON = "comparison"
    GENERAL_QA = "general_qa"


@dataclass
class QueryClassification:
    """Result of query classification."""

    query_type: QueryType
    confidence: float
    keywords_matched: List[str]
    file_hints_matched: List[str]
    needs_clarification: bool
    clarification_message: Optional[str] = None
    suggested_types: Optional[List[Dict[str, str]]] = None


class QueryClassifier:
    """Classifies user queries into specific intent types."""

    # High-confidence keyword patterns
    QUERY_PATTERNS = {
        QueryType.RESUME_REVIEW: {
            "keywords": [
                "resume",
                "candidate",
                "applicant",
                "hire",
                "hiring",
                "cv",
                "good fit",
                "qualified",
                "fit for",
                "good candidate",
                "evaluate",
                "evaluation",
                "assess",
                "assessment",
                "background",
                "experience",
                "skills",
                "qualifications",
            ],
            "file_hints": ["resume", "cv", "candidate"],
            "weight": 1.0,
        },
        QueryType.MEETING_PREP: {
            "keywords": [
                "meeting",
                "prep",
                "prepare",
                "preparation",
                "agenda",
                "briefing",
                "conference",
                "call",
                "sync",
                "discussion",
                "tomorrow",
                "next week",
                "scheduled",
                "upcoming meeting",
            ],
            "file_hints": ["agenda", "meeting", "briefing"],
            "weight": 1.0,
        },
        QueryType.CONTRACT_REVIEW: {
            "keywords": [
                "contract",
                "agreement",
                "terms",
                "legal",
                "obligation",
                "deadline",
                "clause",
                "provision",
                "review contract",
                "analyze agreement",
            ],
            "file_hints": ["contract", "agreement"],
            "weight": 1.0,
        },
        QueryType.COMPARISON: {
            "keywords": [
                "compare",
                "comparison",
                "versus",
                "vs",
                "difference",
                "better",
                "best",
                "choose between",
                "pros and cons",
            ],
            "file_hints": [],
            "weight": 1.0,
        },
        QueryType.DOCUMENT_ANALYSIS: {
            "keywords": [
                "summarize",
                "summary",
                "analyze",
                "analysis",
                "extract",
                "key points",
                "main ideas",
                "insights",
                "document",
            ],
            "file_hints": [],
            "weight": 0.8,
        },
        QueryType.GENERAL_QA: {"keywords": [], "file_hints": [], "weight": 0.5},
    }

    def __init__(self):
        self.confidence_threshold_high = 0.7
        self.confidence_threshold_low = 0.4

    def classify(
        self, query: str, file_names: Optional[List[str]] = None
    ) -> QueryClassification:
        """
        Classify a user query into a specific query type.

        Args:
            query: The user's query string
            file_names: Optional list of uploaded file names

        Returns:
            QueryClassification with type, confidence, and clarification info
        """
        query_lower = query.lower()
        file_names = file_names or []
        file_names_lower = [f.lower() for f in file_names]

        scores = {}
        matched_keywords = {}
        matched_file_hints = {}

        # Score each query type
        for query_type, pattern in self.QUERY_PATTERNS.items():
            score = 0.0
            keywords_found = []
            file_hints_found = []

            # Check keywords
            for keyword in pattern["keywords"]:
                if keyword in query_lower:
                    score += pattern["weight"]
                    keywords_found.append(keyword)

            # Check file name hints
            for hint in pattern["file_hints"]:
                for file_name in file_names_lower:
                    if hint in file_name:
                        score += pattern["weight"] * 1.5  # File hints weighted higher
                        file_hints_found.append(hint)
                        break

            scores[query_type] = score
            matched_keywords[query_type] = keywords_found
            matched_file_hints[query_type] = file_hints_found

        # Normalize scores
        max_score = max(scores.values()) if scores else 0
        if max_score > 0:
            normalized_scores = {k: min(v / max_score, 1.0) for k, v in scores.items()}
        else:
            normalized_scores = {k: 0.0 for k in scores.keys()}

        # Get best match
        best_type = max(normalized_scores, key=normalized_scores.get)
        best_score = normalized_scores[best_type]

        # Determine if clarification needed
        needs_clarification = best_score < self.confidence_threshold_low

        # Build clarification info if needed
        clarification_message = None
        suggested_types = None

        if needs_clarification or best_score < self.confidence_threshold_high:
            # Get top 3 candidates
            sorted_types = sorted(
                normalized_scores.items(), key=lambda x: x[1], reverse=True
            )[:3]

            suggested_types = [
                {
                    "type": qt.value,
                    "label": self._get_type_label(qt),
                    "confidence": round(score, 2),
                }
                for qt, score in sorted_types
                if score > 0.1
            ]

            clarification_message = self._generate_clarification_message(
                query, best_type, best_score, suggested_types
            )

        return QueryClassification(
            query_type=best_type,
            confidence=best_score,
            keywords_matched=matched_keywords[best_type],
            file_hints_matched=matched_file_hints[best_type],
            needs_clarification=needs_clarification,
            clarification_message=clarification_message,
            suggested_types=suggested_types if needs_clarification else None,
        )

    def _get_type_label(self, query_type: QueryType) -> str:
        """Get human-readable label for query type."""
        labels = {
            QueryType.RESUME_REVIEW: "Resume/Candidate Evaluation",
            QueryType.MEETING_PREP: "Meeting Preparation",
            QueryType.CONTRACT_REVIEW: "Contract Review",
            QueryType.DOCUMENT_ANALYSIS: "Document Analysis",
            QueryType.COMPARISON: "Document Comparison",
            QueryType.GENERAL_QA: "General Question",
        }
        return labels.get(query_type, "Unknown")

    def _generate_clarification_message(
        self,
        query: str,
        best_type: QueryType,
        confidence: float,
        suggested_types: List[Dict[str, str]],
    ) -> str:
        """Generate a clarification message for ambiguous queries."""
        if confidence < self.confidence_threshold_low:
            return (
                "I'm not sure what type of analysis you need. "
                "Could you help me understand your request better?"
            )
        else:
            type_label = self._get_type_label(best_type)
            return (
                f"It looks like you might want a {type_label}. "
                f"Is this correct, or would you prefer something else?"
            )


# Singleton instance for reuse
_classifier_instance: Optional[QueryClassifier] = None


def get_classifier() -> QueryClassifier:
    """Get or create the query classifier singleton."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = QueryClassifier()
    return _classifier_instance


def classify_query(
    query: str, file_names: Optional[List[str]] = None
) -> QueryClassification:
    """Convenience function to classify a query."""
    return get_classifier().classify(query, file_names)
