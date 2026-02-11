"""Email processor for parsing .eml files and extracting content.

Handles:
- Parsing email headers (to, from, subject, date, message-id, in-reply-to)
- Extracting email body (plain text and HTML)
- Thread detection from References/In-Reply-To headers
- Action item extraction using LLM
- ICS calendar attachment parsing
- Tone analysis support

Usage:
    processor = EmailProcessor()

    # Parse email file
    email_data = await processor.parse_eml("email.eml")

    # Extract action items
    actions = await processor.extract_action_items(email_data["body"])

    # Get thread context (returns list of email dicts)
    thread = processor.get_thread_context([email_data], email_data["thread_id"])
"""

import email
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.policy import default

from app.utils.ics_utils import ICSUtils
from app.services.llm import create_llm_client
from app.services.content_store import ContentStore, create_content_store
from app.models.content_item import ContentItem, SourceType


class EmailProcessor:
    """Process email files (.eml) and extract structured data."""

    def __init__(self):
        self.llm_client = create_llm_client()

    async def parse_eml(self, file_path: str) -> Dict[str, Any]:
        """Parse .eml file and extract content.

        Args:
            file_path: Path to .eml file

        Returns:
            Dict containing:
                - id: Unique identifier
                - subject: Email subject
                - sender: From email address
                - recipients: List of To addresses
                - cc: List of CC addresses
                - body: Plain text body
                - body_html: HTML body (if present)
                - date: Sent date
                - message_id: Message-ID header
                - thread_id: Thread identifier
                - in_reply_to: In-Reply-To header
                - references: References header
                - attachments: List of attachment info
                - calendar_event: Parsed ICS data (if present)
                - metadata: Additional headers
        """
        with open(file_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=default)

        # Extract headers
        subject = msg.get("Subject", "")
        sender = self._extract_email_address(msg.get("From", ""))
        recipients = self._extract_email_addresses(msg.get("To", ""))
        cc = self._extract_email_addresses(msg.get("Cc", ""))
        date_str = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")

        # Parse date
        date = self._parse_date(date_str)

        # Detect thread ID
        thread_id = self._detect_thread_id(message_id, in_reply_to, references)

        # Extract body content
        body, body_html = self._extract_body(msg)

        # Extract attachments (including ICS files)
        attachments = []
        calendar_event = None

        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                filename = part.get_filename()
                content_type = part.get_content_type()

                attachment_info = {
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(part.get_payload(decode=True) or b""),
                }

                # Parse ICS attachments
                if content_type == "text/calendar" or (
                    filename and filename.endswith(".ics")
                ):
                    ics_content = part.get_content()
                    if ics_content:
                        calendar_event = ICSUtils.parse_ics(ics_content)
                        attachment_info["parsed_event"] = calendar_event

                attachments.append(attachment_info)

        # Build result dict
        email_data = {
            "id": str(uuid.uuid4()),
            "subject": subject,
            "sender": sender,
            "sender_name": self._extract_name(msg.get("From", "")),
            "recipients": recipients,
            "cc": cc,
            "body": body,
            "body_html": body_html,
            "date": date.isoformat() if date else None,
            "message_id": message_id,
            "thread_id": thread_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "attachments": attachments,
            "calendar_event": calendar_event,
            "metadata": {
                "content_type": msg.get_content_type(),
                "has_attachments": len(attachments) > 0,
                "has_calendar_event": calendar_event is not None,
            },
        }

        return email_data

    def _extract_email_address(self, header_value: str) -> str:
        """Extract email address from header."""
        if not header_value:
            return ""

        # Match email in format "Name <email@domain.com>" or just "email@domain.com"
        match = re.search(r"<([^>]+)>", header_value)
        if match:
            return match.group(1).strip()

        # Try to find email pattern
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", header_value)
        if match:
            return match.group(0)

        return header_value.strip()

    def _extract_email_addresses(self, header_value: str) -> List[str]:
        """Extract multiple email addresses from header."""
        if not header_value:
            return []

        # Split by comma and extract each
        addresses = []
        for part in header_value.split(","):
            email = self._extract_email_address(part.strip())
            if email:
                addresses.append(email)

        return addresses

    def _extract_name(self, header_value: str) -> str:
        """Extract display name from header."""
        if not header_value:
            return ""

        # Match name in format "Name <email@domain.com>"
        match = re.search(r'^"?([^"<]+)"?\s*<', header_value)
        if match:
            return match.group(1).strip()

        return ""

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string."""
        if not date_str:
            return None

        try:
            # Try email.utils parsing
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_str)
        except:
            pass

        # Try common formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %Z",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None

    def _detect_thread_id(
        self, message_id: str, in_reply_to: str, references: str
    ) -> str:
        """Detect thread ID from email headers."""
        # Use In-Reply-To as thread ID if present
        if in_reply_to:
            return in_reply_to.strip("<>")

        # Use first reference as thread ID
        if references:
            first_ref = references.split()[0]
            return first_ref.strip("<>")

        # Use message ID as thread ID (start of new thread)
        if message_id:
            return message_id.strip("<>")

        # Generate new thread ID
        return str(uuid.uuid4())

    def _extract_body(self, msg) -> tuple:
        """Extract plain text and HTML body from message."""
        plain_text = ""
        html_text = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get_content_disposition()

                # Skip attachments
                if content_disposition == "attachment":
                    continue

                try:
                    if content_type == "text/plain" and not plain_text:
                        plain_text = part.get_content()
                    elif content_type == "text/html" and not html_text:
                        html_text = part.get_content()
                except:
                    pass
        else:
            # Single part message
            content_type = msg.get_content_type()
            try:
                content = msg.get_content()
                if content_type == "text/plain":
                    plain_text = content
                elif content_type == "text/html":
                    html_text = content
                    # Try to extract text from HTML
                    plain_text = self._html_to_text(content)
            except:
                pass

        # If no plain text but have HTML, convert
        if not plain_text and html_text:
            plain_text = self._html_to_text(html_text)

        return plain_text.strip() if plain_text else "", html_text

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to text conversion."""
        # Remove script and style tags
        text = re.sub(
            r"<(script|style)[^>]*>[^<]*</(script|style)>",
            "",
            html,
            flags=re.IGNORECASE,
        )

        # Convert common block elements to newlines
        text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

        # Remove all remaining tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        import html as html_module

        text = html_module.unescape(text)

        # Clean up whitespace
        text = re.sub(r"\n\n+", "\n\n", text)

        return text.strip()

    async def extract_action_items(self, content: str) -> List[str]:
        """Extract action items from email body using LLM.

        Args:
            content: Email body text

        Returns:
            List of action item strings
        """
        if not content or len(content.strip()) < 10:
            return []

        # Truncate if too long
        max_length = 4000
        truncated = content[:max_length] if len(content) > max_length else content

        prompt = f"""Analyze this email and extract action items. Return ONLY a JSON array of strings.

Email content:
{truncated}

Extract explicit or implicit action items like:
- "Please send the report" → "Send the report"
- "Let's meet next week" → "Schedule meeting for next week"
- "Deadline is Friday" → "Complete task by Friday deadline"
- "Can you review?" → "Review document"

Return format: ["action item 1", "action item 2", ...]
If no action items found, return: []
"""

        try:
            response = self.llm_client.generate(prompt)

            # Parse JSON response
            import json

            actions = json.loads(response)

            if isinstance(actions, list):
                return [str(a).strip() for a in actions if a and str(a).strip()]
            elif isinstance(actions, dict) and "actions" in actions:
                return [
                    str(a).strip() for a in actions["actions"] if a and str(a).strip()
                ]
        except Exception as e:
            print(f"Error extracting action items: {e}")
            return []

        return []

    def get_thread_context(
        self, emails: List[Dict[str, Any]], thread_id: str
    ) -> List[Dict[str, Any]]:
        """Get all emails in a thread.

        Args:
            emails: List of email dicts to search
            thread_id: Thread identifier

        Returns:
            List of emails sorted by date (oldest first)
        """
        if not thread_id:
            return []

        # Filter emails by thread_id
        thread_emails = [
            e
            for e in emails
            if e.get("thread_id") == thread_id
            or e.get("in_reply_to", "").strip("<>") == thread_id
            or thread_id in e.get("references", "")
        ]

        # Sort by date (oldest first)
        def get_date(email):
            date_str = email.get("date", "")
            try:
                return datetime.fromisoformat(date_str) if date_str else datetime.min
            except:
                return datetime.min

        thread_emails.sort(key=get_date)

        return thread_emails

    async def get_tone_examples(
        self, sender_email: str, emails: List[Dict[str, Any]], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get previous emails from sender for tone matching.

        Note: In production, this should query ContentStore.
        For now, filters from provided email list.

        Args:
            sender_email: Email address to match
            emails: List of email dicts to search
            limit: Maximum number of examples

        Returns:
            List of email dicts from the sender
        """
        if not sender_email:
            return []

        # Filter emails from sender
        sender_emails = [e for e in emails if e.get("sender") == sender_email]

        # Sort by date (newest first) and limit
        def get_date(email):
            date_str = email.get("date", "")
            try:
                return datetime.fromisoformat(date_str) if date_str else datetime.min
            except:
                return datetime.min

        sender_emails.sort(key=get_date, reverse=True)

        return sender_emails[:limit]

    async def parse_eml_to_content_item(
        self, file_path: str, content_store: ContentStore = None, session_id: str = None
    ) -> ContentItem:
        """Parse .eml file and store as ContentItem.

        Args:
            file_path: Path to .eml file
            content_store: Optional ContentStore instance for persistence
            session_id: Session ID for association

        Returns:
            ContentItem instance (stored if content_store provided)
        """
        from datetime import datetime

        email_data = await self.parse_eml(file_path)

        item = ContentItem(
            id=email_data["id"],
            session_id=session_id,
            source_type=SourceType.EMAIL,
            title=email_data["subject"],
            content=email_data["body"],
            sender=email_data["sender"],
            recipients=email_data["recipients"],
            thread_id=email_data["thread_id"],
            metadata={
                "cc": email_data.get("cc", []),
                "attachments": email_data.get("attachments", []),
                "calendar_event": email_data.get("calendar_event"),
                "message_id": email_data.get("message_id"),
                "references": email_data.get("references"),
                "has_calendar_event": email_data.get("metadata", {}).get(
                    "has_calendar_event", False
                ),
            },
        )

        if email_data["date"]:
            try:
                item.timestamp = datetime.fromisoformat(email_data["date"])
            except (ValueError, TypeError):
                pass

        if content_store:
            stored = await content_store.add_email(
                subject=email_data["subject"],
                sender=email_data["sender"],
                body=email_data["body"],
                recipients=email_data["recipients"],
                thread_id=email_data["thread_id"],
                timestamp=item.timestamp,
                session_id=session_id,
            )
            return stored

        return item

    async def parse_eml_to_content_items(
        self,
        file_paths: list[str],
        content_store: ContentStore = None,
        session_id: str = None,
    ) -> list[ContentItem]:
        """Parse multiple .eml files and store as ContentItems.

        Args:
            file_paths: List of paths to .eml files
            content_store: Optional ContentStore instance for persistence
            session_id: Session ID for association

        Returns:
            List of ContentItem instances
        """
        items = []
        for file_path in file_paths:
            try:
                item = await self.parse_eml_to_content_item(
                    file_path, content_store=content_store, session_id=session_id
                )
                items.append(item)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
        return items


# Factory function
def create_email_processor() -> EmailProcessor:
    """Create EmailProcessor instance."""
    return EmailProcessor()


# Testing commands
if __name__ == "__main__":
    import asyncio

    async def test():
        processor = EmailProcessor()

        # Test action item extraction
        test_email = """
        Hi Team,
        
        Please review the proposal by Friday and send me your feedback.
        Also, let's schedule a meeting next Tuesday to discuss the budget.
        
        Thanks,
        John
        """

        actions = await processor.extract_action_items(test_email)
        print("Extracted actions:", actions)

        # Test ICS detection
        text1 = "Meeting with investor next Tuesday at 2 PM"
        text2 = "Please review the document"

        from app.utils.ics_utils import ICSUtils

        print(
            f"\nShould create event for '{text1}': {ICSUtils.should_create_event(text1)}"
        )
        print(
            f"Should create event for '{text2}': {ICSUtils.should_create_event(text2)}"
        )

    asyncio.run(test())
