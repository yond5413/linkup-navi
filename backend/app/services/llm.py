"""LLM service providing a unified interface for multiple providers."""

import asyncio
import json
import re
import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from openai import OpenAI
from openai import APIStatusError as OpenAI_APIStatusError
from openai import APIError as OpenAI_APIError
import ollama

from app.config import get_settings, AVAILABLE_MODELS, DEFAULT_MODEL


class PlanStep(BaseModel):
    step_id: str
    description: str
    action_type: str
    thought: str = ""
    depends_on: List[str] = []
    parameters: Dict[str, Any] = {}


class PlannerOutput(BaseModel):
    intent: str
    thought: str = ""
    query_type: str = "general_qa"
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
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if self.provider == "openrouter":
            return self._generate_with_retry(
                lambda: self.client.chat.completions.create(
                    model=self.model, messages=messages, **kwargs
                )
            )
        else:
            response = ollama.chat(model=self.model, messages=messages)
            return response["message"]["content"]

    def _generate_with_retry(self, api_call_fn, max_retries: int = 3):
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = api_call_fn()
                return response.choices[0].message.content
            except OpenAI_APIStatusError as e:
                if e.status_code == 503:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)
                    continue
                raise
            except OpenAI_APIError as e:
                error_str = str(e).lower()
                if "capacity" in error_str or "server at capacity" in error_str:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)
                    continue
                raise
        raise Exception(f"Max retries ({max_retries}) exceeded for API call")

    def generate_json(
        self, prompt: str, schema: Dict[str, Any], system: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate JSON using the configured provider."""
        if self.provider == "openrouter":
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
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response: {content}")


def create_llm_client() -> LLMClient:
    return LLMClient()
