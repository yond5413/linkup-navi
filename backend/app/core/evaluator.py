from typing import Optional, Dict, Any, List
from app.tools.base import ToolResult


class SelfEvaluator:
    def __init__(self, llm=None):
        from app.services.llm import LLMClient

        self.llm = llm or LLMClient()

    async def evaluate_step(self, tool_name: str, result: ToolResult) -> Dict[str, Any]:
        if result.success and result.confidence >= 0.7:
            return {
                "success": True,
                "needs_retry": False,
                "suggestion": None,
                "confidence": result.confidence,
            }

        prompt = f"""
Tool '{tool_name}' execution analysis.

Success: {result.success}
Error: {result.error or "None"}
Result preview: {str(result.data)[:500]}

Suggest how to proceed:
1. Retry with different parameters
2. Use a different tool
3. Ask user for clarification
4. Continue to next step

Respond in JSON:
{{"action": "retry|skip|ask|continue", "suggestion": "...", "confidence": 0.0-1.0}}
"""
        response = self.llm.generate_json(prompt, {})
        return {
            "success": result.success,
            "needs_retry": response.get("action") == "retry",
            "suggestion": response.get("suggestion"),
            "confidence": response.get("confidence", 0.0),
        }

    async def evaluate_completion(
        self, goal: str, execution_trace: List[Dict], response: str
    ) -> Dict[str, Any]:
        prompt = f"""
Evaluate if this response successfully accomplishes the user's goal.

Goal: {goal}

Execution trace: {len(execution_trace)} steps executed
Response: {response[:1500]}

Rate from 0-1:
- completeness: How well was the goal achieved?
- quality: Is the response well-formed?
- accuracy: Is the information accurate?

Respond in JSON:
{{"completion_score": 0.0-1.0, "feedback": "...", "suggestions": [], "is_complete": bool}}
"""
        return self.llm.generate_json(prompt, {})

    async def evaluate_plan_quality(
        self, goal: str, plan: Dict, available_tools: List[str]
    ) -> Dict[str, Any]:
        prompt = f"""
Evaluate the quality of this plan for the user's goal.

Goal: {goal}

Plan: {plan}

Available tools: {", ".join(available_tools)}

Check:
1. Are all necessary steps included?
2. Are appropriate tools selected?
3. Is the order logical?
4. Are dependencies handled correctly?

Respond in JSON:
{{"score": 0.0-1.0, "issues": [], "suggestions": []}}
"""
        return self.llm.generate_json(prompt, {})


class LegacyEvaluator:
    """Original evaluator for backward compatibility."""

    def __init__(self, llm=None):
        from app.services.llm import LLMClient

        self.llm = llm or LLMClient()

    async def evaluate_completion(
        self, goal: str, plan: Any, results: dict, briefing: dict
    ) -> dict:
        prompt = f"""
Goal: {goal}
Plan: {plan.model_dump_json() if hasattr(plan, "model_dump_json") else str(plan)}
Results Summary: {list(results.keys())}
Final Response: {briefing.get("raw_response", briefing.get("actionable_briefing", "N/A"))[:2000]}

As an impartial evaluator, analyze if the response successfully accomplishes the user's goal.
"""
        schema = {
            "type": "object",
            "properties": {
                "completion_score": {"type": "number"},
                "feedback": {"type": "string"},
                "suggestions": {"type": "array", "items": {"type": "string"}},
                "is_complete": {"type": "boolean"},
            },
        }
        try:
            return self.llm.generate_json(prompt, schema)
        except:
            return {
                "completion_score": 0.5,
                "feedback": "Evaluation failed",
                "suggestions": [],
                "is_complete": True,
            }


def create_evaluator(llm=None, legacy: bool = False):
    if legacy:
        return LegacyEvaluator(llm)
    return SelfEvaluator(llm)
