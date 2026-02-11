"""Memory-aware planning module that enriches execution plans with context from long-term memory."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.intent_router import Task
from app.services.vector_memory import get_vector_memory_service
from app.services.llm import LLMClient


class ExecutionPlan(BaseModel):
    tasks: List[Task]
    gaps_identified: List[str]
    research_needed: List[str]
    context_from_memory: Dict[str, Any]
    created_at: str = ""
    thought: str = ""

    def __init__(self, **data):
        data["created_at"] = datetime.now().isoformat()
        super().__init__(**data)


class MemoryAwarePlanner:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.vector_memory = get_vector_memory_service()

    async def create_plan(
        self,
        goal: str,
        tasks: List[Task],
        session_id: str,
        file_context: Optional[Dict[str, str]] = None,
        session_goal: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan enriched with context from memory.

        Process:
        1. Query FAISS for related content
        2. Identify gaps in available context
        3. Determine research needs
        4. Build execution plan with context

        Args:
            goal: The user's goal/intent
            tasks: Decomposed tasks from TaskRouter
            session_id: Current session identifier
            file_context: Available file contents
            session_goal: Long-term session goal

        Returns:
            ExecutionPlan with memory context and gap analysis
        """
        memory_context = await self._query_memory(goal, session_id)
        gaps = await self._identify_gaps(tasks, memory_context, file_context)
        research_needed = await self._determine_research_needs(tasks, memory_context)

        context_summary = self._summarize_context(
            memory_context, file_context, session_goal
        )

        schema = {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "High-level strategy for executing these tasks",
                },
                "enriched_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_type": {"type": "string"},
                            "target": {"type": "string"},
                            "parameters": {"type": "object"},
                            "context_hint": {
                                "type": "string",
                                "description": "Relevant context from memory to consider",
                            },
                        },
                        "required": ["task_type", "target"],
                    },
                },
                "gaps_identified": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Missing information that should be flagged",
                },
                "research_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entities or topics requiring external research",
                },
                "memory_context": {
                    "type": "object",
                    "description": "Relevant context retrieved from memory",
                },
            },
            "required": [
                "thought",
                "enriched_tasks",
                "gaps_identified",
                "research_needed",
                "memory_context",
            ],
        }

        system_prompt = """You are a memory-aware planning engine. Your role is to enrich task execution with context from long-term memory and identify gaps.

Guidelines:
1. Use memory context to provide hints for each task
2. Identify what information is missing (gaps)
3. Suggest what needs external research
4. Maintain consistency with previous interactions
5. Adapt task parameters based on memory context

Return a valid JSON object matching the provided schema."""

        prompt = f"""
GOAL: {goal}

DECOMPOSED TASKS:
{self._format_tasks(tasks)}

MEMORY CONTEXT:
{context_summary}

Instructions:
1. Review each task and note relevant context from memory
2. Identify any gaps in information needed to complete tasks
3. Determine what external research would help
4. Provide execution hints for each task

Respond with enriched task details, gaps, research needs, and memory context.
"""

        try:
            result = self.llm.generate_json(prompt, schema, system_prompt)
            enriched_tasks = []
            for t in result.get("enriched_tasks", []):
                params = t.get("parameters", {})
                if "context_hint" in t and t["context_hint"]:
                    params["context_hint"] = t["context_hint"]
                enriched_tasks.append(
                    Task(
                        task_type=t["task_type"], target=t["target"], parameters=params
                    )
                )

            return ExecutionPlan(
                tasks=enriched_tasks,
                gaps_identified=result.get("gaps_identified", gaps),
                research_needed=result.get("research_needed", research_needed),
                context_from_memory=result.get("memory_context", memory_context),
                thought=result.get("thought", ""),
            )
        except Exception as e:
            return self._fallback_plan(
                goal, tasks, memory_context, gaps, research_needed
            )

    async def _query_memory(self, query: str, session_id: str) -> Dict[str, Any]:
        """Query FAISS vector memory for relevant context."""
        try:
            results = self.vector_memory.query_memory(query, top_k=5)
            return {
                "query": query,
                "results": results,
                "vector_count": self.vector_memory.get_vector_count(),
            }
        except Exception as e:
            return {"query": query, "results": [], "error": str(e)}

    async def _identify_gaps(
        self,
        tasks: List[Task],
        memory_context: Dict[str, Any],
        file_context: Optional[Dict[str, str]],
    ) -> List[str]:
        """Identify missing information needed to complete tasks."""
        gaps = []
        task_targets = [t.target for t in tasks]

        if not memory_context.get("results") and not file_context:
            gaps.append("No relevant context found in memory or files")

        for target in task_targets:
            if "email" in target.lower():
                if not file_context or not any(
                    "email" in f.lower() or ".eml" in f.lower()
                    for f in file_context.keys()
                ):
                    gaps.append(f"Email content needed for: {target}")
            elif "document" in target.lower():
                if not file_context:
                    gaps.append(f"Document needed for: {target}")

        return gaps

    async def _determine_research_needs(
        self, tasks: List[Task], memory_context: Dict[str, Any]
    ) -> List[str]:
        """Determine what external research is needed."""
        research_needs = []
        task_targets = [t.target for t in tasks]

        for target in task_targets:
            if "company" in target.lower() or "organization" in target.lower():
                research_needs.append(target)
            elif "person" in target.lower() or "contact" in target.lower():
                research_needs.append(target)

        if not memory_context.get("results"):
            for target in task_targets:
                if target not in research_needs:
                    research_needs.append(target)

        return list(set(research_needs))

    def _summarize_context(
        self,
        memory_context: Dict[str, Any],
        file_context: Optional[Dict[str, str]],
        session_goal: Optional[str],
    ) -> str:
        """Summarize available context for the prompt."""
        parts = []

        if session_goal:
            parts.append(f"Session Goal: {session_goal}")

        if memory_context.get("results"):
            memory_snippets = [
                r.get("text", "")[:200] for r in memory_context["results"][:3]
            ]
            parts.append("Relevant Memory:\n" + "\n---\n".join(memory_snippets))

        if file_context:
            file_names = list(file_context.keys())
            parts.append(f"Available Files: {', '.join(file_names)}")

        return "\n\n".join(parts) if parts else "No prior context available"

    def _format_tasks(self, tasks: List[Task]) -> str:
        """Format tasks for inclusion in prompt."""
        return "\n".join(
            [
                f"- {t.task_type.value}: {t.target}"
                + (f" (params: {t.parameters})" if t.parameters else "")
                for t in tasks
            ]
        )

    def _fallback_plan(
        self,
        goal: str,
        tasks: List[Task],
        memory_context: Dict[str, Any],
        gaps: List[str],
        research_needed: List[str],
    ) -> ExecutionPlan:
        """Create a fallback plan when LLM fails."""
        return ExecutionPlan(
            tasks=tasks,
            gaps_identified=gaps,
            research_needed=research_needed,
            context_from_memory=memory_context,
            thought=f"Executing {len(tasks)} tasks to achieve: {goal}",
        )


def create_memory_aware_planner(llm: Optional[LLMClient] = None) -> MemoryAwarePlanner:
    return MemoryAwarePlanner(llm)
