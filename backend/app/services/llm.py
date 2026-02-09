"""LLM service providing a unified interface for multiple providers."""

import json
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from openai import OpenAI
import ollama

from app.config import get_settings


class PlanStep(BaseModel):
    step_id: str
    description: str
    action_type: str
    depends_on: List[str] = []
    parameters: Dict[str, Any] = {}


class PlannerOutput(BaseModel):
    intent: str
    query_type: str = "general_qa"  # Type of query (resume_review, meeting_prep, etc.)
    steps: List[PlanStep]
    needs_linkup: bool
    entities_to_research: List[str] = []


class BriefingOutput(BaseModel):
    summary: str
    deadlines: List[str]
    risks: List[str]
    research_snippet: str
    actionable_briefing: str


class LLMClient:
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.llm_provider

        if self.provider == "openrouter":
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.settings.openrouter_api_key,
            )
            self.model = self.settings.openrouter_model
        else:
            self.model = self.settings.ollama_model

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        """Generate text using the configured provider."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if self.provider == "openrouter":
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, **kwargs
            )
            return response.choices[0].message.content
        else:
            response = ollama.chat(model=self.model, messages=messages)
            return response["message"]["content"]

    def generate_json(
        self, prompt: str, schema: Dict[str, Any], system: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate JSON using the configured provider."""
        if self.provider == "openrouter":
            # Use native JSON mode for better reliability
            json_prompt = f"{prompt}\n\nRespond only with a JSON object matching this schema: {json.dumps(schema)}"
            content = self.generate(
                json_prompt, system=system, response_format={"type": "json_object"}
            )
        else:
            json_prompt = f"{prompt}\n\nRespond in valid JSON matching this schema: {json.dumps(schema)}"
            content = self.generate(json_prompt, system=system)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback regex for dirty JSON
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response: {content}")


def create_llm_client() -> LLMClient:
    return LLMClient()
