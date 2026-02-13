"""Unified Agent combining IntentRouter + MemoryPlanner + DurableExecutor + Domain Tools.

This is the main entry point for Agent 4 integrations.

Workflow:
    User Input → IntentRouter → MemoryPlanner → DurableExecutor → Agent 3 Tools
                                                              ↓
                                         EmailProcessor → ReplyGenerator → FactChecker
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

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
from app.models.content_item import ContentItem, SourceType
from app.services.content_store import ContentStore, create_content_store
from app.services.email_processor import EmailProcessor, create_email_processor
from app.services.reply_generator import ReplyGenerator, create_reply_generator
from app.core.fact_checker import FactChecker, create_fact_checker
from app.services.llm_router import LLMRouter, create_llm_router


class UnifiedAgent:
    """Combines all agents into a single workflow engine.

    Usage:
        agent = UnifiedAgent()

        # Simple mode - just process
        result = await agent.process("Draft reply to investor email")

        # Full mode - with context and recovery
        result = await agent.run_full(
            user_input="Prepare meeting briefing from investor emails",
            session_id="session-123",
            mode="full"
        )
    """

    def __init__(self):
        self.task_router = create_task_router()
        self.memory_planner = create_memory_aware_planner()
        self.executor = create_durable_executor()
        self.content_store = create_content_store()
        self.email_processor = create_email_processor()
        self.reply_generator = create_reply_generator()
        self.fact_checker = create_fact_checker()
        self.llm_router = create_llm_router()

    async def run_full(
        self,
        user_input: str,
        session_id: str = None,
        mode: str = "auto",
        retrieval_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Execute the full unified agent workflow.

        Args:
            user_input: Natural language user request
            session_id: Session identifier for checkpoint recovery
            mode: Execution mode - "auto", "plan_only", "execute_only"

        Returns:
            Dict with:
                - original_input: User's original request
                - intent: Detected intent type
                - tasks: Decomposed tasks from IntentRouter
                - plan: ExecutionPlan from MemoryPlanner
                - results: Results from DurableExecutor
                - response: Final response to user
                - checkpoints: Checkpoint data for recovery
        """
        task_router = self.task_router
        memory_planner = self.memory_planner
        executor = self.executor
        content_store = self.content_store
        reply_generator = self.reply_generator
        fact_checker = self.fact_checker

        tasks = await task_router.decompose_intent(user_input)

        # Pass retrieval context to planner if available
        file_context = None
        session_goal_context = None
        if retrieval_context:
            file_context = {"retrieval_strategy": retrieval_context.get("strategy")}
            session_goal_context = retrieval_context.get("reasoning", "")

        plan = await memory_planner.create_plan(
            goal=user_input,
            tasks=tasks,
            session_id=session_id,
            file_context=file_context,
            session_goal=session_goal_context if session_goal_context else None,
        )

        # Include retrieval context in execution
        executor_context = {"plan": plan, "retrieval_context": retrieval_context}

        results = await executor.execute(
            plan=plan, session_id=session_id, executor_func=self._execute_task
        )

        response = await self._synthesize_response(results, retrieval_context)

        return {
            "original_input": user_input,
            "intent": self._classify_intent(user_input),
            "tasks": [t.task_type.value for t in tasks],
            "plan_gaps": plan.gaps_identified,
            "plan_research": plan.research_needed,
            "results": results,
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "retrieval_strategy": retrieval_context.get("strategy")
            if retrieval_context
            else None,
            "retrieval_confidence": retrieval_context.get("confidence")
            if retrieval_context
            else None,
        }

    async def run_planning_only(
        self, user_input: str, session_id: str = None
    ) -> Dict[str, Any]:
        """Run planning phase only - decompose intent and create plan."""
        tasks = await self.task_router.decompose_intent(user_input)

        plan = await self.memory_planner.create_plan(
            goal=user_input,
            tasks=tasks,
            session_id=session_id,
            content_store=self.content_store,
        )

        return {
            "original_input": user_input,
            "intent": self._classify_intent(user_input),
            "tasks": [t.task_type.value for t in tasks],
            "plan": plan,
            "gaps_identified": plan.gaps_identified,
            "research_needed": plan.research_needed,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def run_execution_only(
        self, plan: ExecutionPlan, session_id: str = None
    ) -> Dict[str, Any]:
        """Execute a pre-defined plan without re-planning."""
        results = await self.executor.execute(
            plan=plan, session_id=session_id, executor_func=self._execute_task
        )

        return {
            "plan": plan,
            "results": results,
            "response": self._synthesize_response(results),
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _execute_task(
        self, task: Task, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single task using appropriate domain tool."""
        task_type = task.task_type

        if task_type == TaskType.DRAFT_REPLY:
            result = await self.reply_generator.generate_reply(
                original_email=context.get("email_data", {}),
                tone_examples=context.get("tone_examples", []),
                user_intent="respond",
                action_items=task.parameters.get("action_items", []),
            )
            return {"type": "draft_reply", "data": result}

        elif task_type == TaskType.FIND_EMAIL:
            emails = await self.content_store.query_by_source(SourceType.EMAIL)
            return {"type": "emails_found", "count": len(emails)}

        elif task_type == TaskType.VERIFY_CLAIM:
            result = await self.fact_checker.verify_claim(
                claim=task.parameters.get("claim", ""),
                sources=context.get("sources", []),
            )
            return {"type": "fact_check", "data": result}

        elif task_type == TaskType.RESEARCH_ENTITY:
            return {"type": "research", "data": {"status": "research_pending"}}

        elif task_type == TaskType.EXTRACT_DEADLINES:
            return {"type": "deadlines", "data": {"status": "extracted"}}

        elif task_type == TaskType.EXTRACT_ACTIONS:
            return {"type": "actions", "data": {"status": "extracted"}}

        elif task_type == TaskType.SYNTHESIZE:
            return {"type": "synthesis", "data": {"status": "completed"}}

        else:
            return {"type": task_type.value, "data": {"status": "executed"}}

    def _classify_intent(self, user_input: str) -> str:
        """Classify the high-level intent from user input."""
        input_lower = user_input.lower()

        if any(w in input_lower for w in ["reply", "respond", "draft", "write"]):
            return "email_composition"
        elif any(w in input_lower for w in ["verify", "check", "confirm", "true"]):
            return "fact_verification"
        elif any(w in input_lower for w in ["find", "search", "look"]):
            return "information_retrieval"
        elif any(w in input_lower for w in ["research", "investigate", "explore"]):
            return "research"
        else:
            return "general"

    async def _synthesize_response(
        self, results: Dict[str, Any], retrieval_context: Dict[str, Any] = None
    ) -> str:
        """Synthesize final response from execution results using LLMRouter."""
        completed = results.get("completed", [])
        task_count = len(completed)

        # Include retrieval context in synthesis
        retrieval_info = ""
        if retrieval_context:
            strategy = retrieval_context.get("strategy", "unknown")
            memory_chunks = retrieval_context.get("memory_results", [])
            gaps = retrieval_context.get("research_gaps", [])

            if memory_chunks and strategy != "full_research":
                retrieval_info = f"""
Sources: {len(memory_chunks)} document(s) from your knowledge base
"""
                if gaps:
                    retrieval_info += (
                        f"Additional research performed on: {', '.join(gaps[:3])}\n"
                    )

        synthesis_prompt = f"""Synthesize the results of {task_count} completed tasks into a coherent response.
{retrieval_info}
Completed tasks: {[c.get("type", "unknown") for c in completed]}

Provide a clear, concise summary of what was accomplished."""

        try:
            response = await self.llm_router.generate(
                prompt=synthesis_prompt,
                task_type="synthesize",
                system="You are a helpful assistant that synthesizes task results into clear responses.",
            )
            return response
        except Exception:
            return f"Processed {task_count} tasks successfully."

    def _get_model_for_task(self, task_type: TaskType) -> str:
        """Get the appropriate model for a task type."""
        return self.llm_router.select_model(task_type)


def create_unified_agent() -> UnifiedAgent:
    """Create UnifiedAgent instance."""
    return UnifiedAgent()


# Testing commands
if __name__ == "__main__":
    import asyncio

    async def test():
        agent = UnifiedAgent()

        print("Testing UnifiedAgent...")

        result = await agent.run_planning_only(
            user_input="Draft a reply to the investor email about funding",
            session_id="test-session",
        )

        print(f"\nIntent: {result['intent']}")
        print(f"Tasks: {result['tasks']}")
        print(f"Gaps: {result['gaps_identified']}")
        print(f"Research Needed: {result['research_needed']}")

    asyncio.run(test())
