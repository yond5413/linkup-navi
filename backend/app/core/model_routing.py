"""Model routing configuration for task-to-model mapping.

Maps task complexity to appropriate LLM models for optimal performance/cost.
Uses hardcoded model tiers based on available free models in AVAILABLE_MODELS.
"""

from typing import Dict
from app.config import DEFAULT_MODEL, AVAILABLE_MODELS

SIMPLE_MODEL = "stepfun/step-3.5-flash:free"
MEDIUM_MODEL = "arcee-ai/trinity-large-preview:free"
COMPLEX_MODEL = "meta-llama/llama-3.3-70b-instruct:fallback"

TASK_COMPLEXITY_MAP: Dict[str, str] = {
    "find_email": SIMPLE_MODEL,
    "find_document": SIMPLE_MODEL,
    "extract_deadlines": SIMPLE_MODEL,
    "extract_actions": SIMPLE_MODEL,
    "extract_context": MEDIUM_MODEL,
    "match_tone": MEDIUM_MODEL,
    "draft_reply": MEDIUM_MODEL,
    "summarize": MEDIUM_MODEL,
    "verify_claim": COMPLEX_MODEL,
    "synthesize": COMPLEX_MODEL,
    "research_entity": COMPLEX_MODEL,
}

FALLBACK_MAP: Dict[str, str] = {
    SIMPLE_MODEL: MEDIUM_MODEL,
    MEDIUM_MODEL: COMPLEX_MODEL,
    COMPLEX_MODEL: MEDIUM_MODEL,
}


def get_model_for_task(task_type: str) -> str:
    """Get the appropriate model for a given task type."""
    return TASK_COMPLEXITY_MAP.get(task_type.lower(), DEFAULT_MODEL)


def get_fallback_model(model_id: str) -> str:
    """Get the fallback model for a given model."""
    return FALLBACK_MAP.get(model_id, DEFAULT_MODEL)


def get_model_by_complexity(complexity: str) -> str:
    """Get model by complexity level (simple/medium/complex)."""
    complexity_map = {
        "simple": SIMPLE_MODEL,
        "medium": MEDIUM_MODEL,
        "complex": COMPLEX_MODEL,
    }
    return complexity_map.get(complexity, DEFAULT_MODEL)


def get_available_models() -> list:
    """Return all available models with their tiers."""
    return [
        {"id": SIMPLE_MODEL, "tier": "simple", "name": "Step-3.5 Flash"},
        {"id": MEDIUM_MODEL, "tier": "medium", "name": "Arcee Trinity"},
        {"id": COMPLEX_MODEL, "tier": "complex", "name": "Llama 3.3 70B"},
    ]
