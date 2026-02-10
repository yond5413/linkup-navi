from typing import Optional, Dict, Any
from app.core.planner import PlannerOutput
from app.services.llm import LLMClient


class Evaluator:
    """Evaluates plan execution and provides LLM-powered self-critique."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    async def evaluate_completion(
        self, goal: str, plan: PlannerOutput, results: dict, briefing: dict
    ) -> dict:
        """Use the LLM to evaluate if the results actually meet the user goal."""
        
        prompt = f"""
Goal: {goal}
Plan: {plan.model_dump_json()}
Results Summary: {list(results.keys())}
Final Response: {briefing.get('raw_response', briefing.get('actionable_briefing', 'N/A'))[:2000]}

As an impartial evaluator, analyze if the response successfully accomplishes the user's goal.
Consider:
1. Did we execute all necessary steps?
2. Is the response professional and actionable?
3. Did we miss any entities mentioned in the goal?
"""

        schema = {
            "type": "object",
            "properties": {
                "completion_score": {"type": "number", "description": "Score from 0.0 to 1.0"},
                "feedback": {"type": "string", "description": "Detailed critique of the output"},
                "suggestions": {"type": "array", "items": {"type": "string"}},
                "is_complete": {"type": "boolean"},
            },
            "required": ["completion_score", "feedback", "suggestions", "is_complete"]
        }

        try:
            evaluation = self.llm.generate_json(
                prompt, 
                schema, 
                system="You are an expert AGI evaluator. Be critical and ensure high quality results."
            )
            return evaluation
        except Exception as e:
            # Fallback to simple logic if LLM fails
            return self._fallback_evaluate(goal, results, briefing)

    def _fallback_evaluate(self, goal: str, results: dict, briefing: dict) -> dict:
        score = 0.5 if briefing.get("actionable_briefing") else 0.2
        return {
            "completion_score": score,
            "feedback": "Evaluation fallback used due to LLM error.",
            "suggestions": ["Manually review the briefing for quality."],
            "is_complete": score >= 0.7,
        }

    async def critique_output(self, output: dict) -> dict:
        """Legacy method for checking for errors."""
        issues = []
        if not output.get("briefing"):
            issues.append("Missing briefing output")
        if output.get("results"):
            for step_id, result in output["results"].items():
                if isinstance(result, dict) and "error" in result:
                    issues.append(f"Step {step_id} failed: {result['error']}")

        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "is_acceptable": len(issues) == 0,
        }


def create_evaluator(llm: Optional[LLMClient] = None) -> Evaluator:
    return Evaluator(llm)
