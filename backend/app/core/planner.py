"""Planning module using Qwen for intent inference and goal decomposition."""

from typing import Optional
from app.services.llm import LLMClient, PlannerOutput, PlanStep
from app.core.query_classifier import QueryType


class Planner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    SYSTEM_PROMPT = """You are an intelligent document and research assistant.
Your primary directive is to transform user goals into concrete, executable plans that answer their specific questions.

Guidelines:
1. UNDERSTAND: Identify the user's core question or task
2. DECOMPOSE: Break the goal into logical steps based on query type
3. CONTEXTUALIZE: Use document content to inform what steps are needed
4. KNOWLEDGE GAP: Include research steps when external information would help
5. ACTIONABLE: Always end with a synthesis step that answers the user's question

Adapt your plan based on the query type:
- Resume/Candidate Review: Focus on evaluation, skills extraction, fit assessment
- Meeting Prep: Focus on agenda, deadlines, action items, background research  
- Contract Review: Focus on terms, obligations, deadlines, risks
- Document Analysis: Focus on summarization, key points, insights
- Comparison: Focus on side-by-side analysis of multiple documents

Always respond with a valid JSON object matching the provided schema."""

    async def plan(
        self,
        user_goal: str,
        query_type: str,
        file_context: dict[str, str],
        session_goal: str,
    ) -> PlannerOutput:
        context_summary = self._summarize_context(file_context, session_goal)

        # Get query-type specific instructions
        query_instructions = self._get_query_instructions(query_type)

        prompt = f"""
USER COMMAND: {user_goal}

QUERY TYPE: {query_type}

AVAILABLE FILES & CONTEXT:
{context_summary}

INSTRUCTIONS:
1. Infer the user's core Intent - what specific question are they trying to answer?
2. Formulate 3-5 distinct execution steps appropriate for a {query_type} task.
3. Determine if Linkup research is required (when external knowledge about entities would help).
4. Identify any specific entities to research (companies, people, technologies, etc.).

{query_instructions}

The final step should ALWAYS be 'synthesize' to generate the response that directly answers the user's question.
"""

        schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "Brief description of user's specific intent/question",
                },
                "query_type": {
                    "type": "string",
                    "description": "Confirmed query type",
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
                                    "extract_skills",
                                    "research",
                                    "synthesize",
                                    "list_files",
                                    "compare",
                                    "extract_key_terms",
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
                query_type=result.get("query_type", query_type),
                steps=[PlanStep(**s) for s in result.get("steps", [])],
                needs_linkup=result.get("needs_linkup", False),
                entities_to_research=result.get("entities_to_research", []),
            )
        except Exception as e:
            return self._fallback_plan(user_goal, query_type)

    def _get_query_instructions(self, query_type: str) -> str:
        """Get specific instructions based on query type."""
        instructions = {
            "resume_review": """SUGGESTED STEPS for Resume Review:
- List/Verify Files
- Extract Key Skills & Experience
- Summarize Career Progression
- Research Background (if company/role context provided)
- Evaluate Candidate Fit
- Synthesize Assessment""",
            "meeting_prep": """SUGGESTED STEPS for Meeting Prep:
- List/Verify Files
- Extract Deadlines & Obligations
- Summarize Agenda & Key Content
- Research Entities (attendees, companies, topics)
- Synthesize Meeting Briefing""",
            "contract_review": """SUGGESTED STEPS for Contract Review:
- List/Verify Files
- Extract Key Terms & Conditions
- Identify Deadlines & Dates
- Extract Obligations (both parties)
- Synthesize Contract Analysis""",
            "document_analysis": """SUGGESTED STEPS for Document Analysis:
- List/Verify Files
- Summarize Content
- Extract Key Points & Insights
- Research Context (if needed)
- Synthesize Analysis""",
            "comparison": """SUGGESTED STEPS for Comparison:
- List/Verify Files
- Summarize Each Document
- Extract Comparison Criteria
- Identify Key Differences
- Synthesize Comparison""",
            "general_qa": """SUGGESTED STEPS for General Q&A:
- List/Verify Files
- Search for Relevant Content
- Research External Context (if needed)
- Synthesize Answer""",
        }
        return instructions.get(query_type, instructions["general_qa"])

    def _summarize_context(
        self, file_contents: dict[str, str], session_goal: str
    ) -> str:
        lines = []
        if session_goal:
            lines.append(f"Session goal: {session_goal}")
        for name, content in file_contents.items():
            preview = content[:500] + "..." if len(content) > 500 else content
            lines.append(f"File '{name}':\n{preview}")
        return "\n".join(lines) if lines else "No files uploaded"

    def _fallback_plan(
        self, user_goal: str, query_type: str = "general_qa"
    ) -> PlannerOutput:
        """Create a fallback plan when LLM fails."""
        lower_goal = user_goal.lower()

        # Build steps based on query type
        if query_type == "resume_review":
            steps = [
                PlanStep(
                    step_id="step_1",
                    description="Summarize uploaded resume",
                    action_type="summarize",
                    depends_on=[],
                    parameters={},
                ),
                PlanStep(
                    step_id="step_2",
                    description="Extract key skills and experience",
                    action_type="extract_skills",
                    depends_on=["step_1"],
                    parameters={},
                ),
                PlanStep(
                    step_id="step_3",
                    description="Synthesize candidate evaluation",
                    action_type="synthesize",
                    depends_on=["step_1", "step_2"],
                    parameters={},
                ),
            ]
        elif query_type == "meeting_prep":
            steps = [
                PlanStep(
                    step_id="step_1",
                    description="Summarize uploaded documents",
                    action_type="summarize",
                    depends_on=[],
                    parameters={},
                ),
                PlanStep(
                    step_id="step_2",
                    description="Extract deadlines and obligations",
                    action_type="extract_deadlines",
                    depends_on=["step_1"],
                    parameters={},
                ),
                PlanStep(
                    step_id="step_3",
                    description="Synthesize meeting briefing",
                    action_type="synthesize",
                    depends_on=["step_1", "step_2"],
                    parameters={},
                ),
            ]
        else:
            steps = [
                PlanStep(
                    step_id="step_1",
                    description="Summarize uploaded documents",
                    action_type="summarize",
                    depends_on=[],
                    parameters={},
                ),
                PlanStep(
                    step_id="step_2",
                    description="Synthesize response",
                    action_type="synthesize",
                    depends_on=["step_1"],
                    parameters={},
                ),
            ]

        # Detect if research is needed
        needs_linkup = any(
            word in lower_goal
            for word in [
                "company",
                "corp",
                "inc",
                "llc",
                "meeting with",
                "who is",
                "what is",
            ]
        )

        # Extract entities
        entities = []
        import re

        matches = re.findall(
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s+(?:Corp|Inc|LLC|Company))?)",
            user_goal,
        )
        entities.extend([m for m in matches if len(m) > 2])

        return PlannerOutput(
            intent=user_goal,
            query_type=query_type,
            steps=steps,
            needs_linkup=needs_linkup,
            entities_to_research=entities,
        )


def create_planner(llm: Optional[LLMClient] = None) -> Planner:
    if llm is None:
        llm = LLMClient()
    return Planner(llm)
