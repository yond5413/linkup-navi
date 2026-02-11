"""Email-focused agent combining EmailProcessor + ReplyGenerator.

Usage:
    email_agent = EmailAgent()
    result = await email_agent.process_incoming(
        eml_file="investor_update.eml",
        draft_reply=True
    )
"""

from typing import Dict, Any, List, Optional

from app.services.email_processor import EmailProcessor, create_email_processor
from app.services.reply_generator import ReplyGenerator, create_reply_generator
from app.services.content_store import ContentStore, create_content_store
from app.core.fact_checker import FactChecker, create_fact_checker
from app.models.content_item import ContentItem, SourceType


class EmailAgent:
    """Unified agent for email processing and reply generation."""

    def __init__(self):
        self.processor = create_email_processor()
        self.generator = create_reply_generator()
        self.store = create_content_store()
        self.fact_checker = create_fact_checker()

    async def process_incoming(
        self,
        eml_file: str,
        session_id: str = None,
        draft_reply: bool = True,
        verify_claims: bool = True,
    ) -> Dict[str, Any]:
        """Process incoming email and optionally draft reply.

        Args:
            eml_file: Path to .eml file
            session_id: Session ID
            draft_reply: Whether to generate reply
            verify_claims: Whether to fact-check claims in email

        Returns:
            Dict with email_data, actions, reply (optional), verifications (optional)
        """
        email_data = await self.processor.parse_eml(eml_file)

        actions = await self.processor.extract_action_items(email_data["body"])

        stored_item = None
        if session_id:
            stored_item = await self.processor.parse_eml_to_content_item(
                eml_file, content_store=self.store, session_id=session_id
            )

        result = {
            "email": email_data,
            "action_items": actions,
            "thread_id": email_data.get("thread_id"),
            "stored_item_id": stored_item.id if stored_item else None,
        }

        if draft_reply:
            tone_examples = await self._get_tone_examples(email_data["sender"])

            reply = await self.generator.generate_reply(
                original_email=email_data,
                tone_examples=tone_examples,
                user_intent="respond",
                action_items=actions,
            )
            result["reply"] = reply

        if verify_claims:
            verifications = []
            for action in actions:
                if "?" not in action:
                    verification = await self.fact_checker.verify_claim(action)
                    verifications.append(verification)
            result["verifications"] = verifications

        return result

    async def process_multiple(
        self, eml_files: List[str], session_id: str = None, draft_reply: bool = True
    ) -> List[Dict[str, Any]]:
        """Process multiple email files.

        Args:
            eml_files: List of paths to .eml files
            session_id: Session ID
            draft_reply: Whether to generate replies

        Returns:
            List of results for each email
        """
        results = []
        for eml_file in eml_files:
            result = await self.process_incoming(
                eml_file=eml_file, session_id=session_id, draft_reply=draft_reply
            )
            results.append(result)
        return results

    async def generate_reply_with_store(
        self,
        original_email: Dict[str, Any],
        sender_email: str,
        user_intent: str = "respond",
        action_items: List[str] = None,
    ) -> Dict[str, Any]:
        """Generate reply using ContentStore for tone examples.

        Args:
            original_email: Email dict
            sender_email: Sender to query tone examples for
            user_intent: User's intent
            action_items: Action items to address

        Returns:
            Reply result with tone metadata
        """
        return await self.generator.generate_reply_with_store(
            original_email=original_email,
            content_store=self.store,
            sender_email=sender_email,
            user_intent=user_intent,
            action_items=action_items,
        )

    async def _get_tone_examples(self, sender_email: str) -> List[Dict[str, Any]]:
        """Get tone examples from ContentStore for a sender."""
        emails = await self.store.query_by_source(SourceType.EMAIL)
        sender_emails = [e for e in emails if e.sender == sender_email]

        return [
            {
                "body": item.content,
                "subject": item.title,
                "sender": item.sender,
                "date": item.timestamp.isoformat() if item.timestamp else None,
            }
            for item in sender_emails[:5]
        ]

    async def get_thread(self, thread_id: str) -> List[ContentItem]:
        """Get all emails in a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            List of ContentItems in the thread
        """
        return await self.store.query_by_thread(thread_id)


def create_email_agent() -> EmailAgent:
    """Create EmailAgent instance."""
    return EmailAgent()


# Testing commands
if __name__ == "__main__":
    import asyncio

    async def test():
        agent = EmailAgent()

        print("Testing EmailAgent...")

        result = await agent.process_incoming(
            eml_file="test.eml",
            session_id="test-session",
            draft_reply=True,
            verify_claims=True,
        )

        print(f"\nSubject: {result['email']['subject']}")
        print(f"Sender: {result['email']['sender']}")
        print(f"Thread ID: {result['thread_id']}")
        print(f"Action Items: {len(result['action_items'])}")

        if result.get("reply"):
            print(f"\nReply Tone Score: {result['reply']['tone_score']}")
            print(f"Reply Confidence: {result['reply']['confidence']}")

        if result.get("verifications"):
            print(f"\nVerifications: {len(result['verifications'])}")

    asyncio.run(test())
