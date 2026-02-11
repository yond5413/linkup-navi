"""Adaptive LLM Router for task-based model selection.

Routes tasks to appropriate LLM models based on complexity,
with automatic fallback to ensure reliability.
"""

import logging
from typing import Optional, Dict, Any, Union
from openai import (
    OpenAI,
    APIStatusError as OpenAI_APIStatusError,
    APIError as OpenAI_APIError,
)

from app.config import get_settings
from app.core.model_routing import (
    TASK_COMPLEXITY_MAP,
    FALLBACK_MAP,
    SIMPLE_MODEL,
    MEDIUM_MODEL,
    COMPLEX_MODEL,
    DEFAULT_MODEL,
)
from app.services.llm import create_llm_client

logger = logging.getLogger(__name__)


class LLMRouter:
    """Routes LLM requests to appropriate models based on task complexity.

    Usage:
        router = LLMRouter()
        result = await router.generate("prompt", task_type="verify_claim")
    """

    def __init__(self, llm_client=None):
        self.settings = get_settings()
        self.llm_client = llm_client or create_llm_client()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.settings.openrouter_api_key,
        )

    def select_model(self, task_type: str) -> str:
        """Select the appropriate model for a task type."""
        return TASK_COMPLEXITY_MAP.get(task_type, DEFAULT_MODEL)

    def select_model_by_complexity(self, complexity: str) -> str:
        """Select model by complexity level (simple/medium/complex)."""
        complexity_map = {
            "simple": SIMPLE_MODEL,
            "medium": MEDIUM_MODEL,
            "complex": COMPLEX_MODEL,
        }
        return complexity_map.get(complexity, DEFAULT_MODEL)

    async def generate(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        model: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate response using the appropriate model for the task.

        Args:
            prompt: The user prompt
            task_type: Task type string to route appropriately (used if model not specified)
            model: Specific model to use (overrides task_type routing)
            system: System prompt
            **kwargs: Additional arguments for OpenAI API

        Returns:
            Generated response string
        """
        if model is None:
            if task_type is None:
                model = self.settings.openrouter_model
            else:
                model = self.select_model(task_type)

        return await self._generate_with_fallback(prompt, model, system, **kwargs)

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        task_type: Optional[str] = None,
        model: Optional[str] = None,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate JSON response using the appropriate model."""
        import json

        if model is None:
            if task_type is None:
                model = self.settings.openrouter_model
            else:
                model = self.select_model(task_type)

        json_prompt = f"{prompt}\n\nRespond only with a JSON object matching this schema: {json.dumps(schema)}"

        content = await self._generate_with_fallback(
            json_prompt, model, system, response_format={"type": "json_object"}
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response: {content}")

    async def _generate_with_fallback(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate with automatic fallback to backup models."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_retries = 3
        base_delay = 2
        current_model = model

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=current_model, messages=messages, **kwargs
                )
                return response.choices[0].message.content

            except OpenAI_APIStatusError as e:
                if e.status_code == 503:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Model {current_model} unavailable, retrying in {delay}s"
                    )
                    await self._sleep(delay)
                    continue
                fallback_model = FALLBACK_MAP.get(current_model)
                if fallback_model and fallback_model != current_model:
                    logger.warning(
                        f"Model {current_model} failed, falling back to {fallback_model}"
                    )
                    current_model = fallback_model
                    continue
                raise

            except OpenAI_APIError as e:
                error_str = str(e).lower()
                if "capacity" in error_str or "server at capacity" in error_str:
                    fallback_model = FALLBACK_MAP.get(current_model)
                    if fallback_model and fallback_model != current_model:
                        logger.warning(
                            f"Model {current_model} at capacity, falling back to {fallback_model}"
                        )
                        current_model = fallback_model
                        continue
                raise

        raise Exception(f"Max retries ({max_retries}) exceeded for all models")

    async def _sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio

        await asyncio.sleep(seconds)

    async def health_check(self, model_id: str) -> bool:
        """Check if a specific model is available."""
        try:
            self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.warning(f"Model {model_id} health check failed: {e}")
            return False


def create_llm_router() -> LLMRouter:
    """Create LLMRouter instance."""
    return LLMRouter()
