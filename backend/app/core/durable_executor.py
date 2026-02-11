"""Durable execution module with checkpointing and crash recovery."""

import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from app.core.memory_planner import ExecutionPlan
from app.core.checkpoint import create_checkpoint_manager


@dataclass
class Checkpoint:
    task_index: int
    task_id: str
    task_result: Dict[str, Any]
    timestamp: str
    completed_tasks: List[Dict[str, Any]]
    plan_summary: Dict[str, Any]

    def __init__(self, **kwargs):
        kwargs.setdefault("timestamp", datetime.now().isoformat())
        self.task_index = kwargs.get("task_index", 0)
        self.task_id = kwargs.get("task_id", "")
        self.task_result = kwargs.get("task_result", {})
        self.timestamp = kwargs.get("timestamp", "")
        self.completed_tasks = kwargs.get("completed_tasks", [])
        self.plan_summary = kwargs.get("plan_summary", {})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(**data)


class DurableExecutor:
    def __init__(self):
        pass

    async def execute_with_recovery(
        self,
        plan: ExecutionPlan,
        session_id: str,
        executor_func: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a plan with checkpointing and crash recovery.

        Process:
        1. Check for existing checkpoint
        2. If checkpoint exists, resume from there
        3. Execute each task, saving checkpoint after each
        4. On crash, resume from last checkpoint
        5. Return consolidated results

        Args:
            plan: ExecutionPlan from MemoryAwarePlanner
            session_id: Session identifier for checkpoint persistence
            executor_func: Function to execute a single task (task_type, target, params) -> result

        Returns:
            Consolidated results from all tasks
        """
        checkpoint_manager = create_checkpoint_manager(session_id)
        existing_checkpoint = checkpoint_manager.load()

        results = {
            "task_results": [],
            "gaps_revisited": [],
            "research_findings": [],
            "synthesis": None,
            "checkpoint_recovered": False,
        }

        start_index = 0
        if existing_checkpoint:
            start_index = existing_checkpoint.get("task_index", 0) + 1
            results["checkpoint_recovered"] = True
            results["task_results"] = existing_checkpoint.get("completed_tasks", [])
            print(f"Resuming from checkpoint at task index {start_index}")

        tasks = plan.tasks

        for i in range(start_index, len(tasks)):
            task = tasks[i]
            task_result = None

            try:
                if executor_func:
                    task_result = await executor_func(
                        task.task_type.value, task.target, task.parameters
                    )
                else:
                    task_result = await self._default_execute(task, plan)

                checkpoint_data = {
                    "task_index": i,
                    "task_id": task.task_type.value,
                    "task_result": task_result
                    if isinstance(task_result, dict)
                    else {"result": str(task_result)},
                    "completed_tasks": results["task_results"]
                    + [
                        {
                            "task_type": task.task_type.value,
                            "target": task.target,
                            "result": task_result,
                        }
                    ],
                    "plan_summary": {
                        "goal": plan.thought,
                        "total_tasks": len(tasks),
                        "gaps": plan.gaps_identified,
                        "research_needed": plan.research_needed,
                    },
                }

                checkpoint_manager.save(
                    step_id=f"task_{i}",
                    thought=f"Completed {task.task_type.value}: {task.target}",
                    working_memory=checkpoint_data,
                    completed_steps=[
                        t.get("task_type") for t in checkpoint_data["completed_tasks"]
                    ],
                    agent_mode="durable_execution",
                )

                results["task_results"].append(
                    {
                        "task_type": task.task_type.value,
                        "target": task.target,
                        "result": task_result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                if task_result and isinstance(task_result, dict):
                    if task_result.get("gap_identified"):
                        results["gaps_revisited"].append(task_result["gap_detail"])
                    if task_result.get("research_findings"):
                        results["research_findings"].append(
                            task_result["research_findings"]
                        )

            except Exception as e:
                error_result = {
                    "error": str(e),
                    "task": task.task_type.value,
                    "target": task.target,
                }
                print(f"Task {i} failed: {e}")
                results["task_results"].append(error_result)

                checkpoint_data = {
                    "task_index": i,
                    "task_id": task.task_type.value,
                    "task_result": error_result,
                    "completed_tasks": results["task_results"],
                    "plan_summary": {
                        "goal": plan.thought,
                        "total_tasks": len(tasks),
                        "error": str(e),
                    },
                }

                checkpoint_manager.save(
                    step_id=f"task_{i}_failed",
                    thought=f"Task failed: {task.task_type.value} - {str(e)}",
                    working_memory=checkpoint_data,
                    completed_steps=[
                        t.get("task_type") for t in checkpoint_data["completed_tasks"]
                    ],
                    agent_mode="durable_execution_error",
                )

                results["error"] = str(e)
                break

        results["execution_summary"] = {
            "total_tasks": len(tasks),
            "completed_tasks": len(
                [r for r in results["task_results"] if not r.get("error")]
            ),
            "failed_tasks": len([r for r in results["task_results"] if r.get("error")]),
            "start_time": None,
            "end_time": datetime.now().isoformat(),
        }

        if checkpoint_manager.exists():
            checkpoint_manager.clear()

        return results

    async def _default_execute(self, task, plan: ExecutionPlan) -> Dict[str, Any]:
        """Default task execution when no executor_func provided."""
        context_hint = task.parameters.get("context_hint", "")

        return {
            "task_type": task.task_type.value,
            "target": task.target,
            "executed": True,
            "context_used": bool(context_hint),
            "result_summary": f"Executed {task.task_type.value} for {task.target}",
        }

    async def checkpoint(
        self,
        session_id: str,
        task_index: int,
        task_id: str,
        result: Any,
        completed_tasks: List[Dict[str, Any]],
        plan_summary: Dict[str, Any],
    ):
        """Save checkpoint to SQLite via checkpoint manager."""
        checkpoint_manager = create_checkpoint_manager(session_id)
        checkpoint_data = {
            "task_index": task_index,
            "task_id": task_id,
            "task_result": result
            if isinstance(result, dict)
            else {"result": str(result)},
            "completed_tasks": completed_tasks,
            "plan_summary": plan_summary,
        }
        checkpoint_manager.save(
            step_id=f"task_{task_index}",
            thought=f"Checkpoint after {task_id}",
            working_memory=checkpoint_data,
            completed_steps=[t.get("task_type") for t in completed_tasks],
            agent_mode="durable_execution",
        )

    async def get_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """Get latest checkpoint for session."""
        checkpoint_manager = create_checkpoint_manager(session_id)
        data = checkpoint_manager.load()
        if data:
            return Checkpoint.from_dict(data)
        return None

    async def clear_checkpoint(self, session_id: str):
        """Clear checkpoint for session."""
        checkpoint_manager = create_checkpoint_manager(session_id)
        checkpoint_manager.clear()

    def get_checkpoint_timestamp(self, session_id: str) -> Optional[str]:
        """Get timestamp of latest checkpoint."""
        checkpoint_manager = create_checkpoint_manager(session_id)
        return checkpoint_manager.get_timestamp()


def create_durable_executor() -> DurableExecutor:
    return DurableExecutor()
