"""Intent-aware task routing module for dynamic task decomposition."""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.llm import LLMClient


class TaskType(Enum):
    FIND_EMAIL = "find_email"
    FIND_DOCUMENT = "find_document"
    EXTRACT_CONTEXT = "extract_context"
    EXTRACT_DEADLINES = "extract_deadlines"
    EXTRACT_ACTIONS = "extract_actions"
    MATCH_TONE = "match_tone"
    DRAFT_REPLY = "draft_reply"
    RESEARCH_ENTITY = "research_entity"
    SYNTHESIZE = "synthesize"
    VERIFY_CLAIM = "verify_claim"
    SUMMARIZE = "summarize"


class Task(BaseModel):
    task_type: TaskType
    target: str
    parameters: Dict[str, Any] = {}


class IntentRoute(BaseModel):
    confidence: float
    reasoning: str
    parameters: Dict[str, Any] = {}


class TaskRouter:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    async def decompose_intent(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """
        Dynamically decompose user intent into executable tasks.

        Example: "Draft reply to investor email about funding"
        → [FIND_EMAIL("investor email"), EXTRACT_CONTEXT("funding discussion"),
           MATCH_TONE("investor@vc.com"), DRAFT_REPLY("funding update")]

        Args:
            user_input: The user's natural language request
            context: Optional context including recent messages, available files, etc.

        Returns:
            List of Task objects in execution order
        """
        schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of how the intent was interpreted",
                },
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_type": {
                                "type": "string",
                                "enum": [t.value for t in TaskType],
                            },
                            "target": {
                                "type": "string",
                                "description": "What to search for or act upon",
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Additional parameters for the task",
                            },
                        },
                        "required": ["task_type", "target"],
                    },
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score for the decomposition",
                },
            },
            "required": ["reasoning", "tasks", "confidence"],
        }

        system_prompt = """You are an expert task decomposition engine. Your role is to break down complex user requests into a sequence of atomic, executable tasks.

Available Task Types:
- find_email: Locate specific emails by sender, subject, or content
- find_document: Find documents, PDFs, or files
- extract_context: Pull relevant context from available sources
- extract_deadlines: Identify dates, deadlines, and time-sensitive items
- extract_actions: Identify action items, todo's, and commitments
- match_tone: Find examples of writing style to match
- draft_reply: Generate a response based on context and tone
- research_entity: Look up information about companies, people, or topics
- synthesize: Combine findings into a coherent response
- verify_claim: Cross-reference claims with sources
- summarize: Create concise summaries of content

Guidelines:
1. Decompose into the minimum number of tasks needed
2. Tasks should be executable in the order specified
3. Each task should produce output useful for subsequent tasks
4. Use context from previous tasks as parameters for dependent tasks
5. Always end with synthesize when producing a final response
6. For email replies: find_email → extract_context → match_tone → draft_reply → synthesize

Return a valid JSON object matching the provided schema."""

        context_info = ""
        if context:
            context_parts = []
            if context.get("recent_emails"):
                context_parts.append(f"Recent emails: {context['recent_emails']}")
            if context.get("available_files"):
                context_parts.append(f"Available files: {context['available_files']}")
            if context.get("session_goal"):
                context_parts.append(f"Session goal: {context['session_goal']}")
            if context_info := "\n".join(context_parts):
                context_info = f"\n\nCONTEXT:\n{context_info}"

        prompt = f"""{user_input}{context_info}

Decompose this request into executable tasks. Consider what information is needed and in what order."""

        try:
            result = self.llm.generate_json(prompt, schema, system_prompt)
            tasks = []
            for t in result.get("tasks", []):
                tasks.append(
                    Task(
                        task_type=TaskType(t["task_type"]),
                        target=t["target"],
                        parameters=t.get("parameters", {}),
                    )
                )
            return tasks
        except Exception as e:
            return self._fallback_decompose(user_input)

    def _fallback_decompose(self, user_input: str) -> List[Task]:
        """Create a simple task decomposition when LLM fails."""
        lower_input = user_input.lower()

        if "email" in lower_input or "reply" in lower_input or "draft" in lower_input:
            return [
                Task(
                    task_type=TaskType.FIND_EMAIL,
                    target="relevant email",
                    parameters={},
                ),
                Task(
                    task_type=TaskType.EXTRACT_CONTEXT,
                    target="email content",
                    parameters={},
                ),
                Task(task_type=TaskType.SYNTHESIZE, target="response", parameters={}),
            ]
        elif "deadline" in lower_input or "date" in lower_input:
            return [
                Task(
                    task_type=TaskType.FIND_DOCUMENT,
                    target="relevant document",
                    parameters={},
                ),
                Task(
                    task_type=TaskType.EXTRACT_DEADLINES,
                    target="dates and deadlines",
                    parameters={},
                ),
            ]
        elif "research" in lower_input or "look up" in lower_input:
            entity = (
                user_input.split("about")[-1].strip()
                if "about" in lower_input
                else user_input
            )
            return [
                Task(task_type=TaskType.RESEARCH_ENTITY, target=entity, parameters={}),
                Task(
                    task_type=TaskType.SYNTHESIZE,
                    target="research findings",
                    parameters={},
                ),
            ]
        else:
            return [
                Task(
                    task_type=TaskType.EXTRACT_CONTEXT,
                    target="relevant content",
                    parameters={},
                ),
                Task(task_type=TaskType.SYNTHESIZE, target="response", parameters={}),
            ]

    def classify_intent(self, user_input: str) -> IntentRoute:
        """
        Classify the user's intent into a route with confidence.

        Returns an IntentRoute with confidence score, reasoning, and parameters.
        """
        lower_input = user_input.lower()

        if any(word in lower_input for word in ["email", "reply", "message", "draft"]):
            return IntentRoute(
                confidence=0.9,
                reasoning="Intent appears to be email-related (reply, draft, or message)",
                parameters={"domain": "email"},
            )
        elif any(
            word in lower_input for word in ["deadline", "date", "when", "schedule"]
        ):
            return IntentRoute(
                confidence=0.85,
                reasoning="Intent appears to be deadline/date-related",
                parameters={"domain": "time_sensitive"},
            )
        elif any(
            word in lower_input
            for word in ["research", "look up", "find information about"]
        ):
            return IntentRoute(
                confidence=0.88,
                reasoning="Intent appears to be research-oriented",
                parameters={"domain": "research"},
            )
        elif any(word in lower_input for word in ["summarize", "summary", "recap"]):
            return IntentRoute(
                confidence=0.92,
                reasoning="Intent appears to be summarization-focused",
                parameters={"domain": "summarization"},
            )
        else:
            return IntentRoute(
                confidence=0.6,
                reasoning="Intent appears to be general query",
                parameters={"domain": "general"},
            )


def create_task_router(llm: Optional[LLMClient] = None) -> TaskRouter:
    return TaskRouter(llm)
