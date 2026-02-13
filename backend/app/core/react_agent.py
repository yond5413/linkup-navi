import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.tools.base import ToolResult, ToolContext
from app.tools.registry import ToolRegistry
from app.services.working_memory import WorkingMemory
from app.services.memory import create_memory
from app.services.llm import LLMClient
from app.core.checkpoint import CheckpointManager
from app.core.entity_extractor import EntityExtractor
from app.db.schema import MessageRepository


@dataclass
class AgentConfig:
    max_iterations: int = 20
    confidence_threshold: float = 0.7
    enable_self_reflection: bool = True
    enable_checkpointing: bool = True


@dataclass
class Action:
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    description: str
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    steps: List[PlanStep]
    intent: str = ""
    thought: str = ""


class ReActAgent:
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.llm = LLMClient()
        self.tool_registry = ToolRegistry
        self.checkpoint_manager = None

    async def run(
        self,
        user_input: str,
        session_id: str,
        files: Dict[str, str] = None,
        mode: str = "react",
    ) -> Dict[str, Any]:
        working_mem = WorkingMemory(session_id)
        working_mem.add_message("user", user_input)
        working_mem.current_goal = user_input

        if files:
            working_mem.add_artifact("files", files)
            entity_research = await self._extract_and_research_entities(
                files, session_id
            )
            if entity_research:
                working_mem.add_artifact("entity_research_list", entity_research)
                working_mem.add_artifact(
                    "entity_research_formatted",
                    self._format_entity_research(entity_research),
                )

        if self.config.enable_checkpointing:
            self.checkpoint_manager = CheckpointManager(session_id)

        if mode == "direct":
            return await self._direct_mode(user_input, working_mem, session_id)
        elif mode == "plan_then_act":
            return await self._plan_then_act_mode(user_input, working_mem, session_id)
        else:
            return await self._react_loop(user_input, working_mem, session_id)

    async def _react_loop(
        self, user_input: str, working_mem: WorkingMemory, session_id: str
    ) -> Dict[str, Any]:
        thought = ""
        iteration = 0
        completed_steps = []

        if self.checkpoint_manager and self.checkpoint_manager.exists():
            checkpoint = self.checkpoint_manager.load()
            if checkpoint:
                thought = checkpoint.get("thought", "")
                completed_steps = checkpoint.get("completed_steps", [])
                working_mem.artifacts = checkpoint.get("working_memory", {})
                iteration = len(completed_steps)

        while iteration < self.config.max_iterations:
            iteration += 1

            thought = await self._reason(user_input, working_mem, thought)

            if self._is_complete(thought):
                working_mem.reflection_notes = f"Completed in {iteration} iterations"
                break

            action = self._parse_action(thought)
            if not action.tool_name:
                action.tool_name = "finalize_response"

            result = await self._execute_action(action, working_mem, session_id)
            working_mem.add_observation(action.tool_name, str(result.data)[:500])

            if result.success:
                completed_steps.append(
                    {"step": iteration, "tool": action.tool_name, "success": True}
                )
            else:
                completed_steps.append(
                    {
                        "step": iteration,
                        "tool": action.tool_name,
                        "success": False,
                        "error": result.error,
                    }
                )

            working_mem.add_artifact(f"tool_result_{iteration}", result.data)

            if self.config.enable_checkpointing and self.checkpoint_manager:
                self.checkpoint_manager.save(
                    step_id=f"step_{iteration}",
                    thought=thought,
                    working_memory=working_mem.artifacts,
                    completed_steps=completed_steps,
                    agent_mode="react",
                )

        if self.checkpoint_manager:
            self.checkpoint_manager.clear()

        return await self._synthesize_response(working_mem, completed_steps)

    async def _reason(
        self, user_input: str, working_mem: WorkingMemory, prev_thought: str
    ) -> str:
        context = working_mem.get_context_for_llm()
        tools_available = self.tool_registry.get_tool_names()
        entity_research = (
            working_mem.get_artifact("entity_research_formatted")
            or "No pre-research conducted."
        )

        prompt = f"""
You are a reasoning agent. Based on the conversation so far, determine your next step.

CRITICAL RESEARCH PROTOCOL:
When documents mention specific companies with funding, acquisitions, or product launches:
1. EXTRACT company names from the document
2. SEARCH specific queries: "[Company] [event] [year]"
3. NEVER search generic terms like "competitor research", "market analysis", or "SWOT"
4. CITE specific dollar amounts, dates, and investors from the research

Pre-researched Entity Information:
{entity_research}

User Goal: {user_input}

Available Tools: {", ".join(tools_available)}

Conversation Context:
{context}

Previous Thought: {prev_thought}

Analyze what has been done, what info is missing, and what tool to use next.

Respond with JSON:
{{"thought": "your reasoning", "action": "tool_name or 'finalize_response'", "params": {{}} or {{"content": "...", "session_id": "..."}}}}
"""
        response = self.llm.generate(
            prompt, system="You are a reasoning agent. Think step by step."
        )
        return response

    def _parse_action(self, thought: str) -> Action:
        try:
            parsed = json.loads(thought)
            return Action(
                tool_name=parsed.get("action", "finalize_response"),
                params=parsed.get("params", {}),
            )
        except json.JSONDecodeError:
            import re

            action_match = re.search(r'"action":\s*"([^"]+)"', thought)
            params_match = re.search(r'"params":\s*(\{[^}]+\})', thought)

            action = action_match.group(1) if action_match else "finalize_response"
            params = {}
            if params_match:
                try:
                    params = json.loads(params_match.group(1))
                except:
                    pass

            return Action(tool_name=action, params=params)

    async def _execute_action(
        self, action: Action, working_mem: WorkingMemory, session_id: str
    ) -> ToolResult:
        tool_info = self.tool_registry.get_tool(action.tool_name)

        if not tool_info:
            return ToolResult(
                success=False, data=None, error=f"Unknown tool: {action.tool_name}"
            )

        func = tool_info["func"]
        ctx = ToolContext(
            session_id=session_id,
            working_memory=working_mem.artifacts,
            user_goal=working_mem.current_goal,
        )

        try:
            if action.tool_name in ["finalize_response", "synthesize"]:
                result_data = await func(
                    sources=action.params.get(
                        "sources", list(working_mem.artifacts.values())
                    ),
                    session_id=session_id,
                    user_goal=working_mem.current_goal,
                )
            elif action.tool_name in ["query_memory", "linkup_search", "web_research"]:
                result_data = await func(
                    query=action.params.get("query", working_mem.current_goal),
                    session_id=session_id,
                )
            else:
                result_data = await func(**action.params, session_id=session_id)

            return ToolResult(success=True, data=result_data)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _is_complete(self, thought: str) -> bool:
        return (
            '"action": "finalize_response"' in thought or "finalize" in thought.lower()
        )

    def _parse_sections(self, response_text: str) -> Dict[str, str]:
        """Parse markdown sections from LLM response."""
        sections = {}

        pattern = r"##\s+(.+?)\n([\s\S]*?)(?=##\s+|\Z)"
        matches = re.findall(pattern, response_text)

        for header, content in matches:
            header_key = header.strip().lower().replace(" ", "_").replace("&", "and")
            sections[header_key] = content.strip()

        if not sections:
            sections["summary"] = response_text.strip()

        return sections

    async def _save_reasoning_message(
        self, session_id: str, thought: str, tool_name: str = "reasoning"
    ):
        """Save reasoning thought as a message."""
        try:
            await MessageRepository.save_message(
                session_id=session_id,
                role="assistant",
                content=thought,
                msg_type="reasoning",
            )
        except Exception:
            pass

    async def _synthesize_response(
        self, working_mem: WorkingMemory, completed_steps: List[Dict]
    ) -> Dict[str, Any]:
        artifacts = working_mem.artifacts
        sources = []

        for key, value in artifacts.items():
            if isinstance(value, str):
                sources.append(value)
            elif isinstance(value, dict) and "result" in value:
                sources.append(str(value["result"]))

        execution_trace = working_mem.execution_trace
        last_thought = ""
        if execution_trace:
            last_thought = execution_trace[-1].get("observation", "")

        prompt = f"""
Synthesize a response based on the agent's execution.

Goal: {working_mem.current_goal}

Steps executed: {len(completed_steps)}
Execution trace: {execution_trace}

Artififacts: {list(artifacts.keys())}

Provide a comprehensive, helpful response with proper markdown sections (## Section Name).

Respond with markdown format including sections like:
## Summary
[Your summary here]

## Analysis
[Your analysis here]

[Add other relevant sections as needed]
"""
        response = self.llm.generate(prompt, system="You are a helpful assistant.")

        sections = self._parse_sections(response)

        if working_mem.reflection_notes:
            final_thought = working_mem.reflection_notes
        else:
            final_thought = last_thought

        return {
            "status": "success",
            "response": response,
            "thought": final_thought,
            "execution_trace": execution_trace,
            "completed_steps": completed_steps,
            "iterations": len(completed_steps),
            "artifacts_keys": list(artifacts.keys()),
            "sections": sections,
        }

    async def _direct_mode(
        self, user_input: str, working_mem: WorkingMemory, session_id: str
    ) -> Dict[str, Any]:
        tools = self.tool_registry.get_tool_names()

        prompt = f"""
Select the best tool for this user request.

User: {user_input}

Available tools: {", ".join(tools)}

Respond with JSON:
{{"tool": "tool_name", "params": {{}}}}
"""
        response = self.llm.generate_json(prompt, {})

        action = Action(
            tool_name=response.get("tool", "finalize_response"),
            params=response.get(
                "params", {"content": user_input, "session_id": session_id}
            ),
        )

        result = await self._execute_action(action, working_mem, session_id)

        return {
            "status": "success" if result.success else "error",
            "response": result.data if result.success else {"error": result.error},
            "tool_used": action.tool_name,
            "agent": "direct",
        }

    async def _plan_then_act_mode(
        self, user_input: str, working_mem: WorkingMemory, session_id: str
    ) -> Dict[str, Any]:
        plan = await self._create_plan(user_input, working_mem)
        results = []

        for step in plan.steps:
            action = Action(tool_name=step.action_type, params=step.parameters)
            result = await self._execute_action(action, working_mem, session_id)
            results.append(
                {
                    "description": step.description,
                    "tool": step.action_type,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                }
            )

        working_mem.add_artifact("plan_results", results)

        return {
            "status": "success",
            "response": await self._synthesize_response(working_mem, []),
            "plan": [
                {"step": s.description, "action": s.action_type} for s in plan.steps
            ],
            "execution_results": results,
            "agent": "plan_then_act",
        }

    async def _create_plan(
        self, user_input: str, working_mem: WorkingMemory
    ) -> ExecutionPlan:
        tools = self.tool_registry.get_tool_names()

        prompt = f"""
Create a step-by-step plan to accomplish this goal.

Goal: {user_input}

Available tools: {", ".join(tools)}

Respond with JSON:
{{
    "intent": "brief description of goal",
    "thought": "strategy explanation",
    "steps": [
        {{"description": "...", "action_type": "tool_name", "parameters": {{}}}}
    ]
}}
"""
        response = self.llm.generate_json(prompt, {})

        steps = [
            PlanStep(
                description=s.get("description", ""),
                action_type=s.get("action_type", "finalize_response"),
                parameters=s.get("parameters", {}),
            )
            for s in response.get("steps", [])
        ]

        return ExecutionPlan(
            steps=steps,
            intent=response.get("intent", user_input),
            thought=response.get("thought", ""),
        )

    async def _extract_and_research_entities(
        self, file_contents: Dict[str, str], session_id: str
    ) -> List[Dict]:
        """Extract entities from files and research them."""
        from app.tools.research_tools import linkup_search

        extractor = EntityExtractor()
        all_research = []
        all_entities = []

        for filename, content in file_contents.items():
            entities = await extractor.extract(content, source_file=filename)
            all_entities.extend(entities)

        top_entities = extractor.get_top_entities(all_entities, limit=3)

        for entity in top_entities:
            queries = extractor.generate_queries(entity, max_queries=2)

            for query in queries:
                try:
                    result = await linkup_search(query=query, session_id=session_id)
                    all_research.append(
                        {
                            "entity": entity.name,
                            "query": query,
                            "result": result,
                            "significance": entity.significance,
                        }
                    )
                except Exception:
                    pass

        return all_research

    def _format_entity_research(self, entity_research: List[Dict]) -> str:
        """Format entity research for prompt insertion."""
        if not entity_research:
            return "No pre-research conducted."

        lines = []
        for r in entity_research:
            result_data = r.get("result", {})
            results = (
                result_data.get("results", []) if isinstance(result_data, dict) else []
            )

            answer_text = ""
            if results:
                if isinstance(results, list) and len(results) > 0:
                    first_result = results[0]
                    answer_text = (
                        first_result.get("answer", "")[:500]
                        if isinstance(first_result, dict)
                        else str(results[0])[:500]
                    )
                elif isinstance(results, dict):
                    answer_text = results.get("answer", "")[:500]

            lines.append(f"Entity: {r['entity']}")
            lines.append(f"Query: {r['query']}")
            lines.append(f"Research: {answer_text}")
            lines.append("")

        return "\n".join(lines)


def create_react_agent(config: AgentConfig = None) -> ReActAgent:
    return ReActAgent(config)
