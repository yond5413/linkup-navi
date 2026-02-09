"""Planning module using Qwen for intent inference and goal decomposition."""

from typing import Optional
from app.services.llm import LLMClient, PlannerOutput, PlanStep


class Planner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    SYSTEM_PROMPT = """You are an advanced AGI-inspired meeting preparation assistant. 
Your primary directive is to transform a vague user goal into a concrete, executable plan.

Guidelines:
1. DECOMPOSE: Break the goal into logical steps (Summarization -> Research -> Synthesis).
2. CONTEXTUALIZE: Use the provided document previews and session context to inform the plan.
3. KNOWLEDGE GAP: If a company, person, or technical term is mentioned, ALWAYS include a 'research' step using Linkup.
4. ACTIONABLE: Ensure the final step is ALWAYS 'synthesize' to create the briefing.

Always respond with a valid JSON object matching the provided schema."""

    async def plan(
        self, user_goal: str, file_context: dict[str, str], session_goal: str
    ) -> PlannerOutput:
        context_summary = self._summarize_context(file_context, session_goal)

        prompt = f"""
USER COMMAND: {user_goal}

AVAILABLE FILES & CONTEXT:
{context_summary}

INSTRUCTIONS:
1. Infer the user's core Intent.
2. Formulate 3-5 distinct execution steps.
3. Determine if Linkup research is required (highly recommended for any entity research).
4. Identify entities to search.

REQUIRED STEPS for Meeting Prep:
- List/Verify Files
- Extract Deadlines & Obligations
- Summarize Key Content
- Research Entities (if any)
- Synthesize Final Briefing
"""

        schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "Brief description of user's intent",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_id": {"type": "string"},
                            "description": {"type": "string"},
                            "action_type": {
                                "type": "string",
                                "enum": [
                                    "summarize",
                                    "extract_deadlines",
                                    "research",
                                    "synthesize",
                                    "list_files",
                                ],
                            },
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "parameters": {"type": "object"},
                        },
                    },
                },
                "needs_linkup": {"type": "boolean"},
                "entities_to_research": {"type": "array", "items": {"type": "string"}},
            },
        }

        try:
            result = self.llm.generate_json(prompt, schema, self.SYSTEM_PROMPT)
            return PlannerOutput(
                intent=result.get("intent", user_goal),
                steps=[PlanStep(**s) for s in result.get("steps", [])],
                needs_linkup=result.get("needs_linkup", False),
                entities_to_research=result.get("entities_to_research", []),
            )
        except Exception as e:
            return self._fallback_plan(user_goal)

    def _summarize_context(
        self, file_contents: dict[str, str], session_goal: str
    ) -> str:
        lines = []
        if session_goal:
            lines.append(f"Session goal: {session_goal}")
        for name, content in file_contents.items():
            preview = content[:200] + "..." if len(content) > 200 else content
            lines.append(f"File '{name}':\n{preview}")
        return "\n".join(lines) if lines else "No files uploaded"

    def _fallback_plan(self, user_goal: str) -> PlannerOutput:
        lower_goal = user_goal.lower()
        steps = [
            PlanStep(
                step_id="step_1",
                description="Summarize uploaded documents",
                action_type="summarize",
                depends_on=[],
                parameters={},
            ),
        ]
        needs_linkup = any(
            word in lower_goal
            for word in ["company", "corp", "inc", "llc", "meeting with"]
        )
        entities = []
        if "acme" in lower_goal:
            entities.append("Acme Corp")
        if "company" in lower_goal or "corp" in lower_goal:
            import re

            matches = re.findall(
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Corp|Inc|LLC))?)", user_goal
            )
            entities.extend(matches)

        return PlannerOutput(
            intent=user_goal,
            steps=steps,
            needs_linkup=needs_linkup,
            entities_to_research=entities,
        )


def create_planner(llm: Optional[LLMClient] = None) -> Planner:
    if llm is None:
        llm = LLMClient()
    return Planner(llm)
