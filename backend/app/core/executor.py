"""Execution engine for running planned steps."""

from typing import Optional
from app.services.llm import LLMClient, BriefingOutput
from app.services.linkup import LinkupClient
from app.services.pdf_parser import PDFParser
from app.core.planner import PlannerOutput, PlanStep


class Executor:
    def __init__(
        self,
        llm: LLMClient,
        linkup: LinkupClient,
        pdf_parser: PDFParser,
    ):
        self.llm = llm
        self.linkup = linkup
        self.pdf_parser = pdf_parser

    async def run(self, plan: PlannerOutput, file_contents: dict[str, str]) -> dict:
        results = {}
        for step in plan.steps:
            if self._can_execute(step, results):
                results[step.step_id] = await self._execute_step(step, file_contents)

        briefing = await self._synthesize_briefing(plan, file_contents, results)
        return {
            "plan": plan.model_dump(),
            "results": results,
            "briefing": briefing,
        }

    def _can_execute(self, step: PlanStep, completed_results: dict) -> bool:
        return all(dep in completed_results for dep in step.depends_on)

    async def _execute_step(
        self, step: PlanStep, file_contents: dict[str, str]
    ) -> dict:
        action = step.action_type
        params = step.parameters

        if action == "summarize":
            return await self._action_summarize(file_contents, params)
        elif action == "extract_deadlines":
            return await self._action_extract_deadlines(file_contents, params)
        elif action == "research":
            return await self._action_research(params.get("entities", []))
        elif action == "synthesize":
            return await self._action_synthesize(file_contents, params)
        elif action == "list_files":
            return {"files": list(file_contents.keys())}
        else:
            return {"error": f"Unknown action type: {action}"}

    async def _action_summarize(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        summaries = {}
        for name, content in file_contents.items():
            summary = self.llm.generate(
                f"Summarize this document concisely (2-3 paragraphs):\n\n{content}",
                system="You are a professional document summarizer. Be concise and extract key points.",
            )
            summaries[name] = summary
        return {"summaries": summaries}

    async def _action_extract_deadlines(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        deadlines = []
        for name, content in file_contents.items():
            extracted = self.pdf_parser.extract_deadlines(content)
            deadlines.extend(extracted)
        return {"deadlines": deadlines}

    async def _action_research(self, entities: list[str]) -> dict:
        research = {}
        for entity in entities:
            info = await self.linkup.get_company_info(entity)
            research[entity] = info
        return {"research": research}

    async def _action_synthesize(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        combined = "\n\n".join(file_contents.values())
        synthesis = self.llm.generate(
            f"""Create a meeting preparation briefing from this information.
Include: agenda summary, key deadlines, risks/considerations, and actionable items.

{combined}""",
            system="You are a professional meeting preparer. Create clear, actionable briefings.",
        )
        return {"synthesis": synthesis}

    async def _synthesize_briefing(
        self,
        plan: PlannerOutput,
        file_contents: dict[str, str],
        step_results: dict,
    ) -> dict:
        summary_parts = []
        all_deadlines = []
        all_risks = []
        research_snippet = ""

        for step_id, result in step_results.items():
            if "summaries" in result:
                for name, summary in result["summaries"].items():
                    summary_parts.append(f"### {name}\n{summary}")
            if "deadlines" in result:
                all_deadlines.extend(result["deadlines"])
            if "synthesis" in result:
                summary_parts.append(result["synthesis"]["synthesis"])
            if "research" in result:
                research_parts = []
                for entity, info in result["research"].items():
                    answer = info.get('answer', 'No research answer available.')
                    sources = info.get('sources', [])
                    source_links = ", ".join([f"[{s.get('name', 'Source')}]({s.get('url', '#')})" for s in sources[:3]])
                    research_parts.append(
                        f"**{entity}**: {answer}\n*Sources: {source_links}*"
                    )
                research_snippet = "\n\n".join(research_parts)

        summary_text = (
            "\n\n".join(summary_parts) if summary_parts else "No summaries available."
        )
        deadline_text = (
            "\n".join(f"- {d['date']}: {d.get('context', '')}" for d in all_deadlines)
            if all_deadlines
            else "No deadlines found."
        )
        risks_text = """- Verify all meeting participants before attendance
- Confirm meeting room/virtual link 15 minutes prior
- Prepare backup questions if agenda topics are covered early"""

        prompt = f"""Generate a concise meeting briefing with the following sections:

## Agenda Summary
{summary_text}

## Key Deadlines
{deadline_text}

## Risks & Considerations
{risks_text}

## Company Research
{research_snippet if research_snippet else "No research needed."}

## Actionable Briefing
Create a concise, professional briefing for the meeting attendee."""

        briefing_text = self.llm.generate(
            prompt,
            system="Create professional, actionable meeting briefings. Be concise and practical.",
        )

        return {
            "summary": summary_text,
            "deadlines": [d["date"] for d in all_deadlines],
            "risks": [
                "Verify participants",
                "Confirm meeting link",
                "Prepare backup questions",
            ],
            "research_snippet": research_snippet,
            "actionable_briefing": briefing_text,
        }


def create_executor(
    llm: Optional[LLMClient] = None,
    linkup: Optional[LinkupClient] = None,
    pdf_parser: Optional[PDFParser] = None,
) -> Executor:
    return Executor(
        llm or LLMClient(),
        linkup or LinkupClient(),
        pdf_parser or PDFParser(),
    )
