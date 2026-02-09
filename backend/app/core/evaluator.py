"""Evaluation and self-critique module."""

from typing import Optional
from app.core.planner import PlannerOutput


class Evaluator:
    """Evaluates plan execution and provides self-critique."""

    def __init__(self, ollama=None):
        self.ollama = ollama

    async def evaluate_completion(
        self, goal: str, plan: PlannerOutput, results: dict, briefing: dict
    ) -> dict:
        score = self._calculate_score(goal, plan, results, briefing)
        feedback = self._generate_feedback(goal, plan, results, briefing)
        suggestions = self._generate_suggestions(goal, plan, results, briefing)

        return {
            "completion_score": score,
            "feedback": feedback,
            "suggestions": suggestions,
            "is_complete": score >= 0.7,
        }

    def _calculate_score(
        self, goal: str, plan: PlannerOutput, results: dict, briefing: dict
    ) -> float:
        score = 0.0
        max_score = 1.0

        plan_executed = len(results) >= len(plan.steps)
        has_briefing = bool(briefing.get("actionable_briefing"))
        has_summary = bool(briefing.get("summary"))
        has_deadlines = bool(briefing.get("deadlines"))

        if plan_executed:
            score += 0.3
        if has_briefing:
            score += 0.3
        if has_summary:
            score += 0.2
        if has_deadlines:
            score += 0.2

        return min(score, max_score)

    def _generate_feedback(
        self, goal: str, plan: PlannerOutput, results: dict, briefing: dict
    ) -> str:
        feedback_parts = []

        if len(results) < len(plan.steps):
            feedback_parts.append(
                f"Partially executed: {len(results)}/{len(plan.steps)} steps completed"
            )
        else:
            feedback_parts.append("All planned steps were executed successfully")

        if briefing.get("actionable_briefing"):
            feedback_parts.append("Briefing generated with actionable items")
        else:
            feedback_parts.append("Warning: Briefing generation may have failed")

        return ". ".join(feedback_parts)

    def _generate_suggestions(
        self, goal: str, plan: PlannerOutput, results: dict, briefing: dict
    ) -> list[str]:
        suggestions = []

        lower_goal = goal.lower()
        if "acme" in lower_goal or "company" in lower_goal:
            if not briefing.get("research_snippet"):
                suggestions.append(
                    "Consider researching the mentioned company for context"
                )

        if not briefing.get("deadlines"):
            suggestions.append(
                "No deadlines found in documents - consider manually adding key dates"
            )

        if "meeting" in lower_goal:
            suggestions.append("Arrive 5-10 minutes early to set up materials")
            suggestions.append("Prepare a notebook for taking notes during the meeting")

        if not suggestions:
            suggestions.append(
                "Review the briefing and customize as needed for your specific context"
            )

        return suggestions

    async def critique_output(self, output: dict) -> dict:
        issues = []
        if not output.get("briefing"):
            issues.append("Missing briefing output")
        if not output.get("plan"):
            issues.append("Missing execution plan")
        if output.get("results"):
            for step_id, result in output["results"].items():
                if "error" in result:
                    issues.append(f"Step {step_id} failed: {result['error']}")

        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "is_acceptable": len(issues) == 0 or all("error" not in i for i in issues),
        }


def create_evaluator(ollama=None) -> Evaluator:
    return Evaluator(ollama)
