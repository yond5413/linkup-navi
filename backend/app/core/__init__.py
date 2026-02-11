"""Core module initialization.

Agent 2 Components:
- IntentRouter: Task decomposition and intent classification
- MemoryPlanner: Memory-aware planning with gap analysis
- DurableExecutor: Checkpointed execution with crash recovery

Agent 3 Components:
- FactChecker: Claim verification with web and local sources
"""

from app.core.planner import Planner
from app.core.executor import Executor
from app.core.evaluator import LegacyEvaluator as Evaluator
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
from app.core.fact_checker import (
    FactChecker,
    FactClaim,
    VerificationReport,
    create_fact_checker,
)

__all__ = [
    # Legacy components
    "Planner",
    "Executor",
    "Evaluator",
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
    # Agent 3 - Domain Features
    "FactChecker",
    "FactClaim",
    "VerificationReport",
    "create_fact_checker",
]
