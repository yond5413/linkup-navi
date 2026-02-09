"""PDF parsing utilities using pdfplumber."""

import pdfplumber
from pathlib import Path
from typing import Optional


class PDFParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text.strip()

    @staticmethod
    def extract_agenda_items(text: str) -> list[dict]:
        lines = text.split("\n")
        items = []
        current_item = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(
                marker in line.lower() for marker in ["agenda", "topic", "discussion"]
            ):
                if current_item:
                    items.append(current_item)
                current_item = {"title": line, "details": ""}
            elif current_item:
                current_item["details"] += line + " "

        if current_item:
            items.append(current_item)

        return items

    @staticmethod
    def extract_deadlines(text: str) -> list[dict]:
        import re

        deadline_patterns = [
            r"(?:due|deadline|by|until)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
            r"(\w+\s+\d{1,2},?\s+\d{4})",
        ]
        deadlines = []
        for pattern in deadline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                deadlines.append({"date": match, "context": "Extracted from document"})
        return deadlines

    @staticmethod
    def summarize(text: str, max_length: int = 500) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(".", 1)[0] + "..."


def create_pdf_parser() -> PDFParser:
    return PDFParser()
