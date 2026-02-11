"""Unified agent layer combining Agents 1, 2, 3.

This module provides high-level agent abstractions that combine:
- Agent 2: IntentRouter, MemoryPlanner, DurableExecutor
- Agent 1: ContentItem, ContentStore
- Agent 3: EmailProcessor, ReplyGenerator, FactChecker
"""

from app.agents.unified_agent import UnifiedAgent, create_unified_agent
from app.agents.email_agent import EmailAgent, create_email_agent

__all__ = [
    "UnifiedAgent",
    "create_unified_agent",
    "EmailAgent",
    "create_email_agent",
]
