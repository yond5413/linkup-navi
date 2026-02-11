from typing import List
from .base import ToolResult, ToolContext
from .registry import tool


@tool(description="Summarize text")
async def summarize(text: str, session_id: str, system_prompt: str = None) -> dict:
    from app.services.llm import LLMClient

    llm = LLMClient()
    summary = llm.generate(
        f"Summarize concisely:\n{text}",
        system=system_prompt
        or "You are a professional summarizer. Be concise and extract key points.",
    )
    return {"summary": summary}


@tool(description="Synthesize multiple sources into a coherent response")
async def synthesize(sources: List[str], session_id: str, user_goal: str) -> dict:
    from app.services.llm import LLMClient

    llm = LLMClient()
    combined = "\n\n".join(sources)
    result = llm.generate(
        f"Synthesize to answer: {user_goal}\n\nSources:\n{combined}",
        system="You are an expert analyst. Synthesize information clearly and accurately.",
    )
    return {"synthesis": result}


@tool(description="Extract skills from text")
async def extract_skills(text: str, session_id: str) -> dict:
    from app.services.llm import LLMClient

    llm = LLMClient()
    result = llm.generate(
        f"""Extract and categorize all skills from this text.

Text:
{text}

Format as:
TECHNICAL SKILLS:
- ...

SOFT SKILLS:
- ...

TOOLS & PLATFORMS:
- ...""",
        system="You are a skilled parser. Extract all relevant skills accurately.",
    )
    return {"skills": result}


@tool(description="Compare multiple documents")
async def compare_documents(documents: List[dict], session_id: str) -> dict:
    from app.services.llm import LLMClient

    llm = LLMClient()
    formatted = "\n".join(
        [
            f"=== {doc.get('name', 'Doc')} ===\n{doc.get('content', '')}"
            for doc in documents
        ]
    )
    result = llm.generate(
        f"Compare these documents:\n\n{formatted}",
        system="You are a comparison expert. Provide objective, balanced comparisons.",
    )
    return {"comparison": result}


@tool(description="Generate structured briefing")
async def generate_briefing(
    summaries: str,
    research: str,
    user_goal: str,
    session_id: str,
    query_type: str = "general",
) -> dict:
    from app.services.llm import LLMClient

    llm = LLMClient()
    from app.core.prompt_templates import get_template_for_query_type

    template = get_template_for_query_type(query_type)
    prompt_data = template.format(
        user_goal=user_goal,
        file_contents="",
        summary_text=summaries,
        skills_text="",
        research_findings=research,
    )
    result = llm.generate(prompt_data["user"], system=prompt_data["system"])
    return {"briefing": result, "query_type": query_type}


@tool(description="Finalize response to user")
async def finalize_response(content: str, session_id: str) -> dict:
    return {"final_response": content}
