from .base import ToolResult, ToolContext
from .registry import tool


@tool(description="Parse PDF file and extract text")
async def parse_pdf(file_path: str, session_id: str) -> dict:
    from app.services.pdf_parser import PDFParser

    parser = PDFParser()
    text = parser.extract_text(file_path)
    return {"text": text, "file_path": file_path}


@tool(description="Extract deadlines from PDF content")
async def extract_deadlines(file_path: str, session_id: str) -> dict:
    from app.services.pdf_parser import PDFParser

    parser = PDFParser()
    content = parser.extract_text(file_path)
    deadlines = parser.extract_deadlines(content)
    return {"deadlines": deadlines, "file_path": file_path}


@tool(description="Extract key terms from PDF")
async def extract_key_terms(file_path: str, session_id: str) -> dict:
    from app.services.pdf_parser import PDFParser

    parser = PDFParser()
    content = parser.extract_text(file_path)
    terms = parser.extract_key_terms(content)
    return {"key_terms": terms, "file_path": file_path}


@tool(description="Get PDF metadata")
async def pdf_metadata(file_path: str, session_id: str) -> dict:
    from app.services.pdf_parser import PDFParser

    parser = PDFParser()
    metadata = parser.get_metadata(file_path)
    return metadata or {"error": "Could not extract metadata"}
