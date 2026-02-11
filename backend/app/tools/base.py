from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolContext(BaseModel):
    session_id: str
    working_memory: Dict[str, Any] = {}
    user_goal: str = ""


class ToolResult(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None
    confidence: float = 1.0


class Tool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        pass
