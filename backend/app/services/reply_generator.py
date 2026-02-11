"""Reply generator for creating context-aware email responses.

Features:
- Generate replies matching sender's tone using LLM
- Tone evaluation and iterative improvement
- Action item detection and ICS calendar export
- Support for different user intents (respond, acknowledge, decline, etc.)

Usage:
    generator = ReplyGenerator()

    # Basic reply generation
    result = await generator.generate_reply(
        original_email=email_data,
        tone_examples=[email1, email2],
        user_intent="respond",
        action_items=["Send cap table"]
    )

    # Reply with calendar export
    result = await generator.generate_reply_with_calendar(
        original_email=email_data,
        action_items=["Meeting next Tuesday at 2pm"],
        output_dir="./calendar/"
    )
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.services.llm import create_llm_client
from app.utils.ics_utils import ICSUtils
from app.services.content_store import ContentStore, create_content_store
from app.models.content_item import ContentItem, SourceType


class ReplyGenerator:
    """Generate email replies with tone matching and calendar integration."""

    def __init__(self):
        self.llm_client = create_llm_client()
        self.min_tone_score = 0.7

    async def generate_reply(
        self,
        original_email: Dict[str, Any],
        tone_examples: List[Dict[str, Any]],
        user_intent: str,
        action_items: List[str] = None,
        max_iterations: int = 2,
    ) -> Dict[str, Any]:
        """Generate reply matching sender's tone.

        Args:
            original_email: Dict with email fields (subject, sender, body, etc.)
            tone_examples: List of previous email dicts from sender for tone reference
            user_intent: User's intent (e.g., "respond", "acknowledge", "decline", "follow up")
            action_items: List of action items to address in reply
            max_iterations: Maximum regeneration attempts if tone score is low

        Returns:
            Dict with:
                - draft: Generated reply text
                - tone_score: 0-1 score of tone match
                - confidence: Overall confidence in reply quality
                - iteration: Number of generation attempts
                - action_items_addressed: Which items were addressed
        """
        action_items = action_items or []

        # Build initial prompt
        prompt = self._build_prompt(
            original_email, tone_examples, user_intent, action_items
        )

        best_draft = None
        best_score = 0.0
        iteration = 0

        # Generate with potential regeneration
        for i in range(max_iterations):
            iteration = i + 1

            # Generate draft
            draft = self.llm_client.generate(prompt)

            # Evaluate tone match
            tone_score = self._evaluate_tone_match(draft, tone_examples)

            # Track best draft
            if tone_score > best_score:
                best_score = tone_score
                best_draft = draft

            # Check if tone is good enough
            if tone_score >= self.min_tone_score:
                break

            # Regenerate with stronger tone guidance
            if i < max_iterations - 1:
                prompt = self._build_refinement_prompt(
                    original_email,
                    tone_examples,
                    user_intent,
                    action_items,
                    draft,
                    tone_score,
                )

        # Calculate overall confidence
        confidence = self._calculate_confidence(best_score, iteration, action_items)

        # Check which action items were addressed
        addressed = self._check_action_items_addressed(best_draft, action_items)

        return {
            "draft": best_draft,
            "tone_score": round(best_score, 2),
            "confidence": round(confidence, 2),
            "iteration": iteration,
            "action_items_addressed": addressed,
            "total_action_items": len(action_items),
            "original_sender": original_email.get("sender"),
            "original_subject": original_email.get("subject"),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _build_prompt(
        self,
        original_email: Dict[str, Any],
        tone_examples: List[Dict[str, Any]],
        user_intent: str,
        action_items: List[str],
    ) -> str:
        """Build prompt for reply generation."""

        # Extract sender name
        sender_name = original_email.get("sender_name", "")
        sender_email = original_email.get("sender", "")
        sender_display = (
            sender_name
            if sender_name
            else sender_email.split("@")[0]
            if sender_email
            else "them"
        )

        # Build tone examples text
        tone_text = ""
        if tone_examples:
            tone_text = "\n\nPrevious emails from this sender (for tone reference):\n"
            for i, example in enumerate(tone_examples[:3], 1):
                body = example.get("body", "")[:500]  # Truncate
                tone_text += f"\nExample {i}:\n{body}\n---\n"

        # Build action items text
        action_text = ""
        if action_items:
            action_text = "\n\nAction items to address:\n"
            for item in action_items:
                action_text += f"- {item}\n"

        prompt = f"""You are writing a professional email reply. Match the tone and style of the sender while addressing the user's intent.

ORIGINAL EMAIL:
From: {sender_display}
Subject: {original_email.get("subject", "")}

{original_email.get("body", "")[:1500]}

USER INTENT: {user_intent}
{tone_text}
{action_text}

INSTRUCTIONS:
1. Match the sender's tone (formal/casual, brief/detailed)
2. Address all action items clearly
3. Be professional and courteous
4. Keep it concise unless the sender is verbose
5. Sign off appropriately

Write only the reply email body (no subject line, no "Subject:" prefix):
"""

        return prompt

    def _build_refinement_prompt(
        self,
        original_email: Dict[str, Any],
        tone_examples: List[Dict[str, Any]],
        user_intent: str,
        action_items: List[str],
        previous_draft: str,
        previous_score: float,
    ) -> str:
        """Build refinement prompt when tone score is low."""

        # Analyze tone characteristics
        tone_chars = self._analyze_tone_characteristics(tone_examples)

        prompt = f"""The previous draft did not sufficiently match the sender's tone (score: {previous_score:.2f}/1.0).

PREVIOUS DRAFT:
{previous_draft}

TONE GUIDANCE:
The sender typically writes emails with these characteristics:
{tone_chars}

Please regenerate the reply with STRONGER adherence to these tone characteristics.

ORIGINAL EMAIL:
Subject: {original_email.get("subject", "")}

{original_email.get("body", "")[:1000]}

Write the improved reply:
"""

        return prompt

    def _analyze_tone_characteristics(self, tone_examples: List[Dict[str, Any]]) -> str:
        """Analyze tone characteristics from examples."""
        if not tone_examples:
            return "- Standard professional tone\n"

        characteristics = []

        # Analyze word count (brief vs verbose)
        total_words = sum(len(e.get("body", "").split()) for e in tone_examples)
        avg_words = total_words / len(tone_examples)

        if avg_words < 50:
            characteristics.append("- Very brief and to-the-point")
        elif avg_words < 150:
            characteristics.append("- Concise and focused")
        else:
            characteristics.append("- Detailed and thorough")

        # Check formality indicators
        all_text = " ".join(e.get("body", "").lower() for e in tone_examples)

        casual_markers = ["hey", "hi", "thanks", "cheers", "best", "let me know"]
        formal_markers = ["dear", "regards", "sincerely", "please", "would you"]

        casual_count = sum(all_text.count(m) for m in casual_markers)
        formal_count = sum(all_text.count(m) for m in formal_markers)

        if casual_count > formal_count:
            characteristics.append("- Casual and friendly style")
        else:
            characteristics.append("- Formal and professional style")

        # Check for questions
        question_count = sum(e.get("body", "").count("?") for e in tone_examples)
        if question_count > len(tone_examples):
            characteristics.append("- Frequently asks questions")

        return "\n".join(characteristics)

    def _evaluate_tone_match(self, draft: str, examples: List[Dict[str, Any]]) -> float:
        """Evaluate how well draft matches tone of examples.

        Uses simple heuristics and LLM for scoring.

        Args:
            draft: Generated reply
            examples: List of tone example emails

        Returns:
            Score between 0 and 1
        """
        if not examples:
            return 0.8  # Default score if no examples

        # Get example texts
        example_texts = [e.get("body", "") for e in examples[:3]]

        # Build evaluation prompt
        examples_text = "\n\n".join(
            f"Example {i + 1}:\n{text[:400]}" for i, text in enumerate(example_texts)
        )

        prompt = f"""Rate how well the draft matches the tone of the examples (0-100).

TONE EXAMPLES:
{examples_text}

DRAFT TO EVALUATE:
{draft}

Consider:
- Formality level match
- Length/style similarity
- Professional voice alignment

Return ONLY a number between 0 and 100 representing the tone match percentage.
"""

        try:
            response = self.llm_client.generate(prompt)

            # Extract number from response
            numbers = re.findall(r"\b\d+\b", response)
            if numbers:
                score = int(numbers[0])
                return min(max(score / 100.0, 0.0), 1.0)
        except Exception as e:
            print(f"Error evaluating tone: {e}")

        # Fallback: simple heuristic
        draft_words = len(draft.split())
        example_words = sum(len(e.get("body", "").split()) for e in examples) / len(
            examples
        )

        # Score based on length similarity (simplified)
        if example_words > 0:
            length_ratio = min(draft_words, example_words) / max(
                draft_words, example_words
            )
            return 0.5 + (length_ratio * 0.3)  # Base 0.5 + up to 0.3 for length match

        return 0.7

    def _calculate_confidence(
        self, tone_score: float, iteration: int, action_items: List[str]
    ) -> float:
        """Calculate overall confidence score."""
        # Base confidence from tone
        confidence = tone_score

        # Penalize multiple iterations slightly
        if iteration > 1:
            confidence *= 0.95

        # Boost for addressing action items (assume addressed if generated)
        if action_items:
            confidence *= 0.95  # Slight uncertainty until verified

        return min(confidence, 1.0)

    def _check_action_items_addressed(
        self, draft: str, action_items: List[str]
    ) -> List[str]:
        """Check which action items appear to be addressed in draft."""
        draft_lower = draft.lower()
        addressed = []

        for item in action_items:
            # Simple keyword matching
            item_keywords = set(item.lower().split()) - {
                "the",
                "a",
                "an",
                "to",
                "for",
                "of",
                "in",
                "on",
                "by",
            }

            # Check if significant keywords appear in draft
            if any(
                keyword in draft_lower for keyword in item_keywords if len(keyword) > 3
            ):
                addressed.append(item)

        return addressed

    async def generate_reply_with_calendar(
        self,
        original_email: Dict[str, Any],
        tone_examples: List[Dict[str, Any]] = None,
        user_intent: str = "respond",
        action_items: List[str] = None,
        output_dir: str = "./calendar_exports/",
        max_iterations: int = 2,
    ) -> Dict[str, Any]:
        """Generate reply and create ICS files for action items with dates.

        Args:
            original_email: Original email dict
            tone_examples: Previous emails for tone matching
            user_intent: User's intent
            action_items: Action items (will filter for calendar events)
            output_dir: Directory to save ICS files
            max_iterations: Max tone refinement iterations

        Returns:
            Dict with all generate_reply fields plus:
                - calendar_exports: List of created ICS file paths
                - events_created: Count of calendar events
        """
        # Generate base reply
        result = await self.generate_reply(
            original_email,
            tone_examples or [],
            user_intent,
            action_items,
            max_iterations,
        )

        # Create calendar events for action items
        calendar_exports = []
        events_created = 0

        if action_items:
            os.makedirs(output_dir, exist_ok=True)

            for i, item in enumerate(action_items):
                if ICSUtils.should_create_event(item):
                    # Extract datetime
                    event_time = ICSUtils.extract_datetime(item)

                    if event_time:
                        # Create ICS content
                        ics_content = ICSUtils.create_event(
                            summary=item,
                            start_time=event_time,
                            description=f"From email: {original_email.get('subject', '')}",
                            attendees=[original_email.get("sender")]
                            if original_email.get("sender")
                            else None,
                        )

                        # Save to file
                        safe_subject = re.sub(
                            r"[^\w\s-]", "", original_email.get("subject", "event")
                        )[:30]
                        filename = (
                            f"{safe_subject}_{i}_{event_time.strftime('%Y%m%d')}.ics"
                        )
                        filepath = os.path.join(output_dir, filename)

                        ICSUtils.save_to_file(ics_content, filepath)
                        calendar_exports.append(filepath)
                        events_created += 1

        result["calendar_exports"] = calendar_exports
        result["events_created"] = events_created

        return result

    def extract_calendar_events(self, action_items: List[str]) -> List[Dict[str, Any]]:
        """Extract potential calendar events from action items.

        Args:
            action_items: List of action item strings

        Returns:
            List of event dicts with summary and datetime
        """
        events = []

        for item in action_items:
            if ICSUtils.should_create_event(item):
                event_time = ICSUtils.extract_datetime(item)
                if event_time:
                    events.append(
                        {
                            "summary": item,
                            "start_time": event_time.isoformat(),
                            "end_time": None,  # Would need to extract duration
                            "has_datetime": True,
                        }
                    )

        return events

    async def generate_reply_with_store(
        self,
        original_email: dict[str, any],
        content_store: ContentStore,
        sender_email: str,
        user_intent: str = "respond",
        action_items: list[str] = None,
        limit: int = 5,
        max_iterations: int = 2,
    ) -> dict[str, any]:
        """Generate reply with ContentStore for tone examples.

        Args:
            original_email: Original email dict
            content_store: ContentStore for querying tone examples
            sender_email: Email address to query tone examples for
            user_intent: User's intent
            action_items: Action items to address
            limit: Max tone examples to retrieve
            max_iterations: Max tone refinement iterations

        Returns:
            Dict with all generate_reply fields plus:
                - tone_examples_used: Number of examples used
                - content_store_queried: True
        """
        sender_emails = await content_store.query_by_source(SourceType.EMAIL)

        tone_examples = [e for e in sender_emails if e.sender == sender_email][:limit]

        tone_example_dicts = [
            {
                "body": item.content,
                "subject": item.title,
                "sender": item.sender,
                "date": item.timestamp.isoformat() if item.timestamp else None,
            }
            for item in tone_examples
        ]

        result = await self.generate_reply(
            original_email,
            tone_example_dicts,
            user_intent,
            action_items,
            max_iterations,
        )

        result["tone_examples_used"] = len(tone_example_dicts)
        result["content_store_queried"] = True

        return result

    async def generate_replies_with_store(
        self,
        original_emails: list[dict[str, any]],
        content_store: ContentStore,
        user_intent: str = "respond",
        action_items_by_email: dict[str, list[str]] = None,
        limit: int = 5,
        max_iterations: int = 2,
    ) -> list[dict[str, any]]:
        """Generate replies for multiple emails using ContentStore.

        Args:
            original_emails: List of original email dicts
            content_store: ContentStore for querying tone examples
            user_intent: User's intent
            action_items_by_email: Dict mapping email index to action items
            limit: Max tone examples per email
            max_iterations: Max tone refinement iterations

        Returns:
            List of reply result dicts
        """
        results = []
        for i, email in enumerate(original_emails):
            sender = email.get("sender", "")
            action_items = (
                action_items_by_email.get(str(i), []) if action_items_by_email else None
            )

            result = await self.generate_reply_with_store(
                original_email=email,
                content_store=content_store,
                sender_email=sender,
                user_intent=user_intent,
                action_items=action_items,
                limit=limit,
                max_iterations=max_iterations,
            )
            results.append(result)

        return results


# Factory function
def create_reply_generator() -> ReplyGenerator:
    """Create ReplyGenerator instance."""
    return ReplyGenerator()


# Testing commands
if __name__ == "__main__":
    import asyncio

    async def test():
        generator = ReplyGenerator()

        # Mock email data
        original = {
            "subject": "Project Update",
            "sender": "client@example.com",
            "sender_name": "John Client",
            "body": "Hi, Can we schedule a call next Tuesday at 2pm to review the proposal? Thanks, John",
        }

        tone_examples = [
            {"body": "Hi, Let's catch up soon. Best, John"},
            {"body": "Thanks for the update. Talk soon, John"},
        ]

        action_items = [
            "Schedule call for next Tuesday at 2pm",
            "Review proposal before call",
        ]

        # Test basic generation
        result = await generator.generate_reply(
            original, tone_examples, "respond", action_items
        )

        print("Generated Reply:")
        print(result["draft"])
        print(f"\nTone Score: {result['tone_score']}")
        print(f"Confidence: {result['confidence']}")
        print(
            f"Action Items Addressed: {len(result['action_items_addressed'])}/{result['total_action_items']}"
        )

        # Test with calendar
        print("\n" + "=" * 50)
        result_with_calendar = await generator.generate_reply_with_calendar(
            original,
            tone_examples,
            "respond",
            action_items,
            output_dir="./test_calendar/",
        )

        print(f"\nCalendar Events Created: {result_with_calendar['events_created']}")
        print(f"ICS Files: {result_with_calendar['calendar_exports']}")

    asyncio.run(test())
