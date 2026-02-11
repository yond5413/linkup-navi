"""Linkup Navi - Multi-Domain Desktop Intelligence Agent.

Architectural Specification v2.0
Vision: A privacy-first, AGI-inspired desktop agent that unifies documents,
emails, messages, and research through semantic memory and intent-aware task routing.

This module provides clean exports for all agent components.
"""

__version__ = "0.1.0"

# =============================================================================
# AGENT 2: Core Intelligence - Intent, Planning, Execution
# =============================================================================

from app.core.intent_router import TaskRouter, TaskType, Task, create_task_router
from app.core.memory_planner import (
    MemoryAwarePlanner,
    ExecutionPlan,
    create_memory_aware_planner,
)
from app.core.durable_executor import (
    DurableExecutor,
    Checkpoint,
    create_durable_executor,
)

# =============================================================================
# AGENT 1: Content Management - Unified Content Storage
# =============================================================================

from app.models.content_item import ContentItem, SourceType
from app.services.content_store import ContentStore, create_content_store

# =============================================================================
# AGENT 3: Domain Features - Email, Replies, Fact-Checking
# =============================================================================

from app.services.email_processor import EmailProcessor, create_email_processor
from app.services.reply_generator import ReplyGenerator, create_reply_generator
from app.core.fact_checker import (
    FactChecker,
    FactClaim,
    VerificationReport,
    create_fact_checker,
)

# =============================================================================
# UNIFIED AGENTS - High-Level Abstractions (Combines 1 + 2 + 3)
# =============================================================================

from app.agents.unified_agent import UnifiedAgent, create_unified_agent
from app.agents.email_agent import EmailAgent, create_email_agent

# =============================================================================
# AGENT 4: Adaptive LLM Routing - Task-based Model Selection
# =============================================================================

from app.core.model_routing import (
    TASK_COMPLEXITY_MAP,
    get_model_for_task,
    get_fallback_model,
    get_model_by_complexity,
)
from app.services.llm_router import LLMRouter, create_llm_router

# =============================================================================
# LEGACY COMPONENTS (For backward compatibility)
# =============================================================================

from app.core.planner import Planner
from app.core.executor import Executor
from app.core.evaluator import LegacyEvaluator as Evaluator

__all__ = [
    # Version
    "__version__",
    # Agent 2 - Core Intelligence
    "TaskRouter",
    "TaskType",
    "Task",
    "create_task_router",
    "MemoryAwarePlanner",
    "ExecutionPlan",
    "create_memory_aware_planner",
    "DurableExecutor",
    "Checkpoint",
    "create_durable_executor",
    # Agent 1 - Content Management
    "ContentItem",
    "SourceType",
    "ContentStore",
    "create_content_store",
    # Agent 3 - Domain Features
    "EmailProcessor",
    "create_email_processor",
    "ReplyGenerator",
    "create_reply_generator",
    "FactChecker",
    "FactClaim",
    "VerificationReport",
    "create_fact_checker",
    # Unified Agents
    "UnifiedAgent",
    "create_unified_agent",
    "EmailAgent",
    "create_email_agent",
    # Agent 4 - Adaptive LLM Routing
    "TASK_COMPLEXITY_MAP",
    "get_model_for_task",
    "get_fallback_model",
    "get_model_by_complexity",
    "LLMRouter",
    "create_llm_router",
    # Legacy
    "Planner",
    "Executor",
    "Evaluator",
]
