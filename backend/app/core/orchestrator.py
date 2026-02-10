"""Agent Orchestrator for managing high-level agent flows, feedback loops, and tracking."""

import logging
from typing import Optional, List, Dict, Any

from app.services.llm import LLMClient, PlannerOutput
from app.services.linkup import LinkupClient
from app.services.pdf_parser import PDFParser
from app.core.planner import Planner
from app.core.executor import Executor
from app.core.evaluator import Evaluator
from app.core.query_classifier import classify_query, QueryType
from app.services.vector_memory import get_vector_memory_service
from app.db.schema import TaskRepository, SessionRepository

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        linkup: Optional[LinkupClient] = None,
        pdf_parser: Optional[PDFParser] = None,
    ):
        self.llm = llm or LLMClient()
        self.linkup = linkup or LinkupClient()
        self.pdf_parser = pdf_parser or PDFParser()
        self.planner = Planner(self.llm)
        self.evaluator = Evaluator(self.llm)

    async def run(
        self,
        session_id: str,
        command: str,
        file_contents: Dict[str, str],
        session_goal: str,
        explicit_entities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run the full agent loop: Classify -> Plan -> Execute -> Evaluate -> Refine."""
        
        # 1. Classify
        file_names = list(file_contents.keys())
        classification = classify_query(command, file_names)
        
        # If clarification needed, handle it (caller should handle return)
        if classification.needs_clarification:
            return {
                "status": "needs_clarification",
                "classification": classification
            }

        # Clear any previous execution state
        Executor.clear_execution_status(session_id)

        # 2. Initialize Task Tracking
        task = None
        try:
            task = await TaskRepository.create_task(
                session_id=session_id,
                user_input=command,
                inferred_intent="Analyzing...",
                tools_used="Classifier",
                status="planning"
            )
        except Exception as e:
            logger.warning(f"Failed to create task record: {e}")

        try:
            # 3. Memory Retrieval
            enriched_goal = command
            try:
                vector_memory = get_vector_memory_service()
                long_term_context = vector_memory.query_memory(command)
                if long_term_context:
                    enriched_goal += f"\n\nLong-term Memory Context:\n" + "\n".join(long_term_context)
            except Exception as e:
                logger.warning(f"Vector memory query failed (non-fatal): {e}")

            # 4. Plan
            plan = await self.planner.plan(
                enriched_goal,
                classification.query_type.value,
                file_contents,
                session_goal,
                explicit_entities,
            )
            
            # Update Task with Plan info
            if task:
                try:
                    tools_used = ", ".join(set(s.action_type for s in plan.steps))
                    await TaskRepository.update_task(task.id, plan.intent, tools_used)
                    await TaskRepository.update_task_status(task.id, "executing")
                except Exception as e:
                    logger.warning(f"Failed to update task: {e}")
            
            # 5. Execute
            executor = Executor(self.llm, self.linkup, self.pdf_parser, session_id=session_id)
            execution_result = await executor.run(plan, file_contents, enriched_goal)
            
            # 6. Evaluate
            try:
                evaluation = await self.evaluator.evaluate_completion(
                    command, plan, execution_result["results"], execution_result["response"]
                )
            except Exception as e:
                logger.warning(f"Evaluation failed (non-fatal): {e}")
                evaluation = {
                    "completion_score": 0.8,
                    "feedback": "Evaluation skipped due to error.",
                    "suggestions": [],
                    "is_complete": True,
                }
            
            # 7. Refine (Loop) — only if score is low
            if evaluation.get("completion_score", 1.0) < 0.7 and not evaluation.get("is_complete", True):
                logger.info(f"Low evaluation score ({evaluation.get('completion_score')}). Refining plan...")
                
                try:
                    refinement_prompt = f"""
                    The previous plan and execution failed to fully satisfy the user goal.
                    FEEDBACK FROM EVALUATOR: {evaluation.get('feedback')}
                    SUGGESTIONS: {", ".join(evaluation.get('suggestions', []))}
                    
                    REVISE THE PLAN to address these issues.
                    """
                    
                    refined_plan = await self.planner.plan(
                        f"{enriched_goal}\n\nREFINEMENT REQUEST:\n{refinement_prompt}",
                        plan.query_type,
                        file_contents,
                        session_goal,
                        explicit_entities
                    )
                    
                    # Re-execute refined plan
                    execution_result = await executor.run(refined_plan, file_contents, enriched_goal)
                    plan = refined_plan
                    
                    # Re-evaluate (best-effort)
                    try:
                        evaluation = await self.evaluator.evaluate_completion(
                            command, refined_plan, execution_result["results"], execution_result["response"]
                        )
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Refinement failed (non-fatal), using original result: {e}")

            # Update task status
            if task:
                try:
                    await TaskRepository.update_task_status(task.id, "completed")
                except Exception as e:
                    logger.warning(f"Failed to update task status: {e}")
            
            return {
                "status": "success",
                "plan": plan.model_dump(),
                "results": execution_result["results"],
                "response": execution_result["response"],
                "evaluation": evaluation,
                "intent": plan.intent,
                "query_type": plan.query_type
            }
        
        except Exception as e:
            logger.error(f"Orchestrator run failed: {e}", exc_info=True)
            # Mark task as failed
            if task:
                try:
                    await TaskRepository.update_task_status(task.id, "failed")
                except Exception:
                    pass
            raise
