"""Ollama client for local LLM inference."""

import ollama
from typing import Optional
from pydantic import BaseModel

from app.config import get_settings


class OllamaClient:
    def __init__(self):
        self.settings = get_settings()
        self.model = self.settings.ollama_model

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = ollama.chat(model=self.model, messages=messages)
        return response["message"]["content"]

    def generate_json(
        self, prompt: str, schema: dict, system: Optional[str] = None
    ) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append(
            {
                "role": "user",
                "content": f"{prompt}\n\nRespond in valid JSON matching this schema: {schema}",
            }
        )

        response = ollama.chat(model=self.model, messages=messages)
        content = response["message"]["content"]
        import json

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Failed to parse JSON from response: {content}")


class PlanStep(BaseModel):
    step_id: str
    description: str
    action_type: str
    depends_on: list[str] = []
    parameters: dict = {}


class PlannerOutput(BaseModel):
    intent: str
    steps: list[PlanStep]
    needs_linkup: bool
    entities_to_research: list[str] = []


class BriefingOutput(BaseModel):
    summary: str
    deadlines: list[str]
    risks: list[str]
    research_snippet: str
    actionable_briefing: str


def create_planner_client() -> OllamaClient:
    return OllamaClient()
