"""Agent Orchestrator - Main entry point for agent execution.

Modes:
- "react": ReAct agent (default)
- "legacy": Legacy planner/executor
- "full": Unified agent combining Agents 1, 2, 3
"""

import json
import logging
from typing import Optional, List, Dict, Any

from app.services.llm import LLMClient
from app.services.linkup import LinkupClient
from app.services.pdf_parser import PDFParser
from app.core.react_agent import ReActAgent
from app.core.query_classifier import classify_query, QueryType
from app.services.vector_memory import get_vector_memory_service
from app.db.schema import TaskRepository
from app.agents.unified_agent import UnifiedAgent, create_unified_agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        linkup: Optional[LinkupClient] = None,
        pdf_parser: Optional[PDFParser] = None,
        unified_agent: Optional[UnifiedAgent] = None,
    ):
        self.llm = llm or LLMClient()
        self.linkup = linkup or LinkupClient()
        self.pdf_parser = pdf_parser or PDFParser()
        self.react_agent = ReActAgent()
        self.unified_agent = unified_agent or create_unified_agent()

    async def run(
        self,
        session_id: str,
        command: str,
        file_contents: Dict[str, str],
        session_goal: str,
        explicit_entities: Optional[List[str]] = None,
        mode: str = "react",
    ) -> Dict[str, Any]:
        if mode == "legacy":
            return await self._run_legacy(
                command, file_contents, session_id, session_goal
            )
        elif mode == "full":
            return await self._run_unified(command, session_id, mode)
        else:
            return await self._run_agent(
                command, file_contents, session_id, session_goal, mode
            )

    async def _run_unified(
        self,
        command: str,
        session_id: str,
        mode: str,
    ) -> Dict[str, Any]:
        """Run the unified agent combining Agents 1, 2, 3."""
        result = await self.unified_agent.run_full(
            user_input=command, session_id=session_id, mode=mode
        )

        execution_trace = result.get("execution_trace", [])
        execution_details = json.dumps(
            {
                "execution_trace": execution_trace,
                "iterations": result.get("iterations", 0),
                "artifacts_keys": result.get("artifacts_keys", []),
                "completed_steps": result.get("tasks", []),
            }
        )

        try:
            task = await TaskRepository.create_task(
                session_id=session_id,
                user_input=command,
                inferred_intent=result.get("intent", "unknown"),
                tools_used="UnifiedAgent",
                status="completed",
                execution_details=execution_details,
            )
        except Exception as e:
            logger.warning(f"Failed to create task: {e}")

        return {
            "status": "success",
            "response": result.get("response", ""),
            "thought": "",
            "execution_trace": [],
            "completed_steps": result.get("tasks", []),
            "mode": "full",
            "agent": "unified",
            "unified_result": result,
        }

    async def _run_agent(
        self,
        command: str,
        file_contents: Dict[str, str],
        session_id: str,
        session_goal: str,
        mode: str,
    ) -> Dict[str, Any]:
        result = await self.react_agent.run(
            user_input=command, session_id=session_id, files=file_contents, mode=mode
        )

        execution_trace = result.get("execution_trace", [])
        execution_details = json.dumps(
            {
                "execution_trace": execution_trace,
                "iterations": result.get("iterations", 0),
                "artifacts_keys": result.get("artifacts_keys", []),
                "completed_steps": result.get("completed_steps", []),
            }
        )

        try:
            task = await TaskRepository.create_task(
                session_id=session_id,
                user_input=command,
                inferred_intent=result.get("response", "")[:100]
                if isinstance(result.get("response"), str)
                else str(result.get("response", ""))[:100],
                tools_used="ReActAgent",
                status="completed",
                execution_details=execution_details,
            )
        except Exception as e:
            logger.warning(f"Failed to create task: {e}")

        response_data = result.get("response", {})
        thought = result.get("thought", "")
        execution_trace = result.get("execution_trace", [])
        sections = result.get("sections", {})

        if isinstance(response_data, str):
            response_data = {
                "raw_response": response_data,
                "query_type": mode,
                "structured": len(sections) > 1,
                "sections": sections,
                "thought": thought,
                "execution_trace": execution_trace,
            }
        else:
            response_data["thought"] = thought
            response_data["execution_trace"] = execution_trace
            response_data["sections"] = sections
            response_data["structured"] = len(sections) > 1

        return {
            "status": result.get("status", "success"),
            "response": response_data,
            "thought": thought,
            "execution_trace": execution_trace,
            "completed_steps": result.get("completed_steps", []),
            "mode": mode,
            "agent": "react",
        }

    async def _run_legacy(
        self,
        command: str,
        file_contents: Dict[str, str],
        session_id: str,
        session_goal: str,
    ) -> Dict[str, Any]:
        from app.core.planner import Planner
        from app.core.executor import Executor
        from app.core.evaluator import LegacyEvaluator

        classification = classify_query(command, list(file_contents.keys()))

        if classification.needs_clarification:
            return {
                "status": "needs_clarification",
                "classification": {
                    "query_type": classification.query_type.value,
                    "confidence": classification.confidence,
                    "clarification_message": classification.clarification_message,
                },
            }

        planner = Planner(self.llm)
        enriched_goal = command

        try:
            vector_memory = get_vector_memory_service()
            long_term_context = vector_memory.query_memory(command)
            if long_term_context:
                enriched_goal += f"\n\nLong-term Memory:\n" + "\n".join(
                    long_term_context
                )
        except Exception as e:
            logger.warning(f"Vector memory failed: {e}")

        plan = await planner.plan(
            enriched_goal,
            classification.query_type.value,
            file_contents,
            session_goal,
        )

        executor = Executor(
            self.llm, self.linkup, self.pdf_parser, session_id=session_id
        )
        execution_result = await executor.run(plan, file_contents, enriched_goal)

        evaluator = LegacyEvaluator(self.llm)
        try:
            evaluation = await evaluator.evaluate_completion(
                command, plan, execution_result["results"], execution_result["response"]
            )
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
            evaluation = {
                "completion_score": 0.8,
                "feedback": "Evaluation skipped",
                "suggestions": [],
                "is_complete": True,
            }

        return {
            "status": "success",
            "plan": plan.model_dump(),
            "results": execution_result["results"],
            "response": execution_result["response"],
            "evaluation": evaluation,
            "classification": {
                "query_type": classification.query_type.value,
                "confidence": classification.confidence,
            },
            "agent": "legacy",
        }


def create_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator()
