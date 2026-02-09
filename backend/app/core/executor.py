"""Execution engine for running planned steps and generating dynamic responses."""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from app.services.llm import LLMClient, PlannerOutput, PlanStep
from app.services.linkup import LinkupClient
from app.services.pdf_parser import PDFParser
from app.core.prompt_templates import get_template_for_query_type


@dataclass
class ExecutionState:
    """Tracks the current execution state for a session."""

    session_id: str
    current_step: str = ""
    reasoning: str = ""
    progress: float = 0.0
    complete: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


# In-memory storage for execution states
_execution_states: dict[str, ExecutionState] = {}

# In-memory storage for execution results
_execution_results: dict[str, dict] = {}


class Executor:
    def __init__(
        self,
        llm: LLMClient,
        linkup: LinkupClient,
        pdf_parser: PDFParser,
        session_id: Optional[str] = None,
    ):
        self.llm = llm
        self.linkup = linkup
        self.pdf_parser = pdf_parser
        self.session_id = session_id

    def _update_state(
        self, step: str, reasoning: str, progress: float, complete: bool = False
    ):
        """Update execution state for the current session."""
        if self.session_id:
            _execution_states[self.session_id] = ExecutionState(
                session_id=self.session_id,
                current_step=step,
                reasoning=reasoning,
                progress=progress,
                complete=complete,
                timestamp=datetime.utcnow(),
            )

    @staticmethod
    def get_execution_status(session_id: str) -> Optional[ExecutionState]:
        """Get the current execution status for a session."""
        return _execution_states.get(session_id)

    @staticmethod
    def clear_execution_status(session_id: str):
        """Clear execution status for a session."""
        if session_id in _execution_states:
            del _execution_states[session_id]

    async def run(
        self, plan: PlannerOutput, file_contents: dict[str, str], user_goal: str
    ) -> dict:
        """Execute the plan and generate a response."""
        results = {}
        total_steps = len(plan.steps)

        # Phase 1: Planning (0-20%)
        self._update_state(
            "Planning", "Analyzing your request and creating an execution plan...", 0.1
        )

        for idx, step in enumerate(plan.steps):
            if self._can_execute(step, results):
                # Calculate progress based on step index (20% to 80%)
                base_progress = 0.2 + (idx / total_steps) * 0.6

                # Update state before executing step
                step_reasoning = self._get_step_reasoning(step)
                self._update_state(
                    self._get_step_display_name(step), step_reasoning, base_progress
                )

                results[step.step_id] = await self._execute_step(step, file_contents)

                # Update state after step completion
                self._update_state(
                    self._get_step_display_name(step),
                    f"Completed {self._get_step_display_name(step)}",
                    base_progress + (0.6 / total_steps),
                )

        # Phase 5: Synthesizing (80-100%)
        self._update_state(
            "Generating response",
            f"Compiling analysis into {plan.query_type.replace('_', ' ')} format...",
            0.85,
        )

        # Generate dynamic response based on query type
        response = await self._generate_response(
            user_goal=user_goal,
            query_type=plan.query_type,
            file_contents=file_contents,
            step_results=results,
        )

        # Mark complete
        self._update_state(
            "Complete", "Response generation completed successfully", 1.0, complete=True
        )

        return {
            "plan": plan.model_dump(),
            "results": results,
            "response": response,
            "query_type": plan.query_type,
        }

    def _get_step_display_name(self, step: PlanStep) -> str:
        """Get a human-readable name for a step."""
        action_names = {
            "summarize": "Analyzing documents",
            "extract_deadlines": "Extracting deadlines",
            "extract_skills": "Extracting skills",
            "research": "Researching entities",
            "synthesize": "Synthesizing information",
            "list_files": "Listing files",
            "compare": "Comparing documents",
            "extract_key_terms": "Extracting key terms",
        }
        return action_names.get(
            step.action_type, step.action_type.replace("_", " ").title()
        )

    def _get_step_reasoning(self, step: PlanStep) -> str:
        """Get reasoning text for a step."""
        reasoning_map = {
            "summarize": "Reading and summarizing uploaded documents to extract key information...",
            "extract_deadlines": "Scanning documents for dates, deadlines, and time-sensitive information...",
            "extract_skills": "Identifying technical skills, soft skills, and qualifications...",
            "research": f"Researching {', '.join(step.parameters.get('entities', ['entities']))} via external data sources...",
            "synthesize": "Combining all analyzed information into actionable insights...",
            "list_files": "Enumerating uploaded files...",
            "compare": "Analyzing differences and similarities between documents...",
            "extract_key_terms": "Identifying key contractual terms and obligations...",
        }
        return reasoning_map.get(step.action_type, f"Executing {step.action_type}...")

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
        elif action == "extract_skills":
            return await self._action_extract_skills(file_contents, params)
        elif action == "research":
            return await self._action_research(params.get("entities", []))
        elif action == "synthesize":
            return await self._action_synthesize(file_contents, params)
        elif action == "list_files":
            return {"files": list(file_contents.keys())}
        elif action == "compare":
            return await self._action_compare(file_contents, params)
        elif action == "extract_key_terms":
            return await self._action_extract_key_terms(file_contents, params)
        else:
            return {"error": f"Unknown action type: {action}"}

    async def _action_summarize(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        """Summarize uploaded documents."""
        summaries = {}
        for name, content in file_contents.items():
            summary = self.llm.generate(
                f"""Summarize this document concisely (2-3 paragraphs):

{content}""",
                system="You are a professional document summarizer. Be concise and extract key points.",
            )
            summaries[name] = summary
        return {"summaries": summaries}

    async def _action_extract_deadlines(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        """Extract deadlines from documents."""
        deadlines = []
        for name, content in file_contents.items():
            extracted = self.pdf_parser.extract_deadlines(content)
            deadlines.extend(extracted)
        return {"deadlines": deadlines}

    async def _action_extract_skills(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        """Extract skills from resume documents."""
        skills = {}
        for name, content in file_contents.items():
            extracted = self.llm.generate(
                f"""Extract and categorize all skills mentioned in this resume.
                
Resume content:
{content}

Format your response as:
TECHNICAL SKILLS:
- List technical skills here

SOFT SKILLS:
- List soft skills here

TOOLS & PLATFORMS:
- List tools/platforms here

OTHER QUALIFICATIONS:
- List certifications, languages, etc.""",
                system="You are a skilled resume parser. Extract all relevant skills and qualifications accurately.",
            )
            skills[name] = extracted
        return {"skills": skills}

    async def _action_research(self, entities: list[str]) -> dict:
        """Research entities using Linkup."""
        research = {}
        for entity in entities:
            info = await self.linkup.get_company_info(entity)
            research[entity] = info
        return {"research": research}

    async def _action_synthesize(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        """Synthesize information from documents."""
        combined = "\n\n".join(file_contents.values())
        synthesis = self.llm.generate(
            f"""Synthesize the key information from these documents into a coherent summary.

{combined}

Provide a structured synthesis covering main points, conclusions, and any decisions or actions needed.""",
            system="You are a professional analyst. Synthesize information clearly and accurately.",
        )
        return {"synthesis": synthesis}

    async def _action_compare(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        """Compare multiple documents."""
        if len(file_contents) < 2:
            return {"comparison": "Need at least 2 documents to compare"}

        comparison = self.llm.generate(
            f"""Compare the following documents side-by-side:

{chr(10).join([f"=== {name} ===\n{content}\n" for name, content in file_contents.items()])}

Provide a comparison highlighting key similarities and differences.""",
            system="You are a comparison expert. Provide objective, balanced comparisons.",
        )
        return {"comparison": comparison}

    async def _action_extract_key_terms(
        self, file_contents: dict[str, str], params: dict
    ) -> dict:
        """Extract key terms from contracts."""
        terms = {}
        for name, content in file_contents.items():
            extracted = self.llm.generate(
                f"""Extract key contractual terms from this document:

{content}

Identify:
- Payment terms
- Duration/term
- Termination clauses
- Liability provisions
- Confidentiality terms
- Any unusual or noteworthy clauses""",
                system="You are a contract analyst. Extract key terms accurately.",
            )
            terms[name] = extracted
        return {"key_terms": terms}

    async def _generate_response(
        self,
        user_goal: str,
        query_type: str,
        file_contents: dict[str, str],
        step_results: dict,
    ) -> dict:
        """
        Generate a dynamic response based on query type using appropriate template.

        This replaces the hardcoded meeting briefing with query-specific responses.
        """
        # Get the appropriate template
        template = get_template_for_query_type(query_type)

        # Aggregate results from steps
        summaries = []
        deadlines = []
        skills = []
        research_findings = []

        for step_id, result in step_results.items():
            if "summaries" in result:
                for name, summary in result["summaries"].items():
                    summaries.append(f"### {name}\n{summary}")
            if "deadlines" in result:
                deadlines.extend(result["deadlines"])
            if "skills" in result:
                for name, skill_text in result["skills"].items():
                    skills.append(f"### {name}\n{skill_text}")
            if "synthesis" in result:
                summaries.append(result["synthesis"])
            if "research" in result:
                for entity, info in result["research"].items():
                    answer = info.get("answer", "No research answer available.")
                    sources = info.get("sources", [])
                    source_links = ", ".join(
                        [
                            f"[{s.get('name', 'Source')}]({s.get('url', '#')})"
                            for s in sources[:3]
                        ]
                    )
                    research_findings.append(
                        f"**{entity}**: {answer}\n*Sources: {source_links}*"
                    )
            if "key_terms" in result:
                for name, terms in result["key_terms"].items():
                    summaries.append(f"### Contract Terms: {name}\n{terms}")
            if "comparison" in result:
                summaries.append(f"### Comparison\n{result['comparison']}")

        # Format content for template
        summary_text = (
            "\n\n".join(summaries) if summaries else "No document summaries available."
        )
        skills_text = "\n\n".join(skills) if skills else "No skills extracted."
        research_text = (
            "\n\n".join(research_findings)
            if research_findings
            else "No external research conducted."
        )

        # Combine file contents
        file_content_text = (
            "\n\n---\n\n".join(
                [
                    f"=== {name} ===\n{content}"
                    for name, content in file_contents.items()
                ]
            )
            if file_contents
            else "No files provided."
        )

        # Format template with variables
        prompt_data = template.format(
            user_goal=user_goal,
            file_contents=file_content_text,
            summary_text=summary_text,
            skills_text=skills_text,
            research_findings=research_text,
        )

        # Generate response using LLM
        response_text = self.llm.generate(
            prompt_data["user"],
            system=prompt_data["system"],
        )

        # Parse structured response
        parsed_response = self._parse_structured_response(
            response_text, template.required_sections, template.optional_sections
        )

        # Add query type to response
        parsed_response["query_type"] = query_type

        return parsed_response

    def _parse_structured_response(
        self,
        response_text: str,
        required_sections: list,
        optional_sections: list = None,
    ) -> dict:
        """
        Parse LLM response into structured sections.

        Expects markdown headers like:
        ## Section Name
        Content here...
        """
        optional_sections = optional_sections or []
        sections = {}

        # Split by markdown headers
        # Pattern matches ## Header or ## Header (with optional spaces)
        pattern = r"##\s+(.+?)\n"
        parts = re.split(pattern, response_text)

        # parts[0] is content before first header (if any)
        # parts[1] is first header, parts[2] is its content, etc.

        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    header = (
                        parts[i].strip().lower().replace(" ", "_").replace("&", "and")
                    )
                    content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                    sections[header] = content

        # If no structured sections found, treat entire response as summary
        if not sections:
            sections["summary"] = response_text
            # Try to extract content for required sections if present
            for section in required_sections:
                # Look for section mentions in text
                section_title = section.replace("_", " ").title()
                if section_title.lower() in response_text.lower():
                    # Try to extract content after section mention
                    pattern = rf"{section_title}[\s:]+(.+?)(?=\n\n|\Z)"
                    match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        sections[section] = match.group(1).strip()

        # Ensure all required sections exist (even if empty)
        for section in required_sections:
            if section not in sections:
                sections[section] = "No information available."

        # Add optional sections if present
        for section in optional_sections:
            if section in sections:
                continue  # Already captured

        return {
            "sections": sections,
            "raw_response": response_text,
            "structured": len(sections) > 1,
        }


def create_executor(
    llm: Optional[LLMClient] = None,
    linkup: Optional[LinkupClient] = None,
    pdf_parser: Optional[PDFParser] = None,
    session_id: Optional[str] = None,
) -> Executor:
    return Executor(
        llm or LLMClient(),
        linkup or LinkupClient(),
        pdf_parser or PDFParser(),
        session_id=session_id,
    )
