"""ICS (iCalendar) utility for parsing and generating calendar events.

Lightweight implementation using only Python standard library.
No external dependencies required.

Usage:
    # Parse ICS content
    event = ICSUtils.parse_ics(ics_content)

    # Generate ICS content
    ics = ICSUtils.create_event(
        summary="Meeting",
        start_time=datetime(2024, 2, 15, 10, 0),
        end_time=datetime(2024, 2, 15, 11, 0)
    )
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


class ICSUtils:
    """Utility class for ICS file operations."""

    # Keywords that suggest calendar event creation
    CALENDAR_KEYWORDS = [
        "meeting",
        "call",
        "sync",
        "discuss",
        "review",
        "deadline",
        "due",
        "submit",
        "present",
        "demo",
        "conference",
        "appointment",
        "schedule",
        "interview",
        "standup",
        "retrospective",
        "planning",
        "workshop",
    ]

    # Date patterns to detect in text
    DATE_PATTERNS = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # MM/DD/YYYY or DD-MM-YY
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",  # YYYY-MM-DD
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s+\d{4})?\b",  # January 15, 2024
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[a-z]*\b",  # Days of week
    ]

    # Time patterns
    TIME_PATTERNS = [
        r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b",  # 10:00 AM
        r"\b\d{1,2}\s*(?:AM|PM|am|pm)\b",  # 10 AM
    ]

    @staticmethod
    def parse_ics(ics_content: str) -> Dict[str, Any]:
        """Parse ICS content and extract event details.

        Args:
            ics_content: Raw ICS file content as string

        Returns:
            Dict with event fields: summary, start, end, location,
            description, attendees, organizer
        """
        event = {
            "summary": "",
            "start": None,
            "end": None,
            "location": "",
            "description": "",
            "attendees": [],
            "organizer": None,
            "uid": None,
        }

        # Simple line-by-line parsing (ICS is text-based)
        lines = ics_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        i = 0
        in_event = False

        while i < len(lines):
            line = lines[i].strip()

            # Handle continuation lines (start with space)
            while i + 1 < len(lines) and lines[i + 1].startswith(" "):
                line += lines[i + 1][1:]
                i += 1

            if line == "BEGIN:VEVENT":
                in_event = True
            elif line == "END:VEVENT":
                in_event = False
            elif in_event:
                if line.startswith("SUMMARY:"):
                    event["summary"] = line[8:]
                elif line.startswith("DTSTART"):
                    event["start"] = ICSUtils._parse_datetime(line)
                elif line.startswith("DTEND"):
                    event["end"] = ICSUtils._parse_datetime(line)
                elif line.startswith("LOCATION:"):
                    event["location"] = line[9:]
                elif line.startswith("DESCRIPTION:"):
                    event["description"] = (
                        line[12:].replace("\\n", "\n").replace("\\,", ",")
                    )
                elif line.startswith("UID:"):
                    event["uid"] = line[4:]
                elif line.startswith("ORGANIZER"):
                    match = re.search(r"mailto:(.+?)(?:$|\r|\n)", line)
                    if match:
                        event["organizer"] = match.group(1)
                elif line.startswith("ATTENDEE"):
                    match = re.search(r"mailto:(.+?)(?:$|\r|\n)", line)
                    if match:
                        event["attendees"].append(match.group(1))

            i += 1

        return event

    @staticmethod
    def _parse_datetime(line: str) -> Optional[datetime]:
        """Parse datetime from ICS DTSTART/DTEND line."""
        # Extract value after colon or semicolon parameters
        match = re.search(r":(\d{8}T?\d{6}Z?)", line)
        if not match:
            return None

        dt_str = match.group(1)

        try:
            if "T" in dt_str:
                # Format: 20240215T100000 or 20240215T100000Z
                dt_str = dt_str.rstrip("Z")
                return datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
            else:
                # Format: 20240215 (all-day event)
                return datetime.strptime(dt_str, "%Y%m%d")
        except ValueError:
            return None

    @staticmethod
    def create_event(
        summary: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        organizer: Optional[str] = None,
        uid: Optional[str] = None,
    ) -> str:
        """Generate ICS content string.

        Args:
            summary: Event title
            start_time: Event start datetime
            end_time: Event end datetime (defaults to 1 hour after start)
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            organizer: Organizer email address
            uid: Unique identifier (auto-generated if not provided)

        Returns:
            ICS content as string
        """
        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        if uid is None:
            uid = str(uuid.uuid4())

        # Format datetime for ICS (UTC format with Z)
        dt_format = "%Y%m%dT%H%M%SZ"
        dt_start = start_time.strftime(dt_format)
        dt_end = end_time.strftime(dt_format)
        dt_stamp = datetime.utcnow().strftime(dt_format)

        # Escape special characters in text fields
        summary_escaped = (
            summary.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )
        desc_escaped = (
            description.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )
        loc_escaped = (
            location.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )

        # Build ICS content
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Linkup Navi//Calendar//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dt_stamp}",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{summary_escaped}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{desc_escaped}")

        if location:
            lines.append(f"LOCATION:{loc_escaped}")

        if organizer:
            lines.append(f"ORGANIZER:mailto:{organizer}")

        if attendees:
            for attendee in attendees:
                lines.append(f"ATTENDEE:mailto:{attendee}")

        lines.extend(["END:VEVENT", "END:VCALENDAR"])

        return "\r\n".join(lines)

    @staticmethod
    def save_to_file(ics_content: str, filename: str) -> str:
        """Save ICS content to file.

        Args:
            ics_content: ICS content string
            filename: Output filename (should end with .ics)

        Returns:
            Absolute path to saved file
        """
        import os

        if not filename.endswith(".ics"):
            filename += ".ics"

        # Ensure directory exists
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(filename, "w", newline="\r\n") as f:
            f.write(ics_content)

        return os.path.abspath(filename)

    @staticmethod
    def should_create_event(text: str) -> bool:
        """Check if text should become a calendar event.

        Uses keyword detection and date/time pattern matching.

        Args:
            text: Text to analyze

        Returns:
            True if text suggests a calendar event
        """
        text_lower = text.lower()

        # Check for calendar keywords
        has_keyword = any(
            keyword in text_lower for keyword in ICSUtils.CALENDAR_KEYWORDS
        )

        # Check for date patterns
        has_date = any(re.search(pattern, text) for pattern in ICSUtils.DATE_PATTERNS)

        # Check for time patterns
        has_time = any(re.search(pattern, text) for pattern in ICSUtils.TIME_PATTERNS)

        # Create event if: has keyword OR (has date AND has time)
        return has_keyword or (has_date and has_time)

    @staticmethod
    def extract_datetime(text: str) -> Optional[datetime]:
        """Extract datetime from text.

        Basic implementation - finds date and time patterns.

        Args:
            text: Text containing date/time information

        Returns:
            datetime object or None
        """
        # Try to find date
        date_match = None
        for pattern in ICSUtils.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                date_match = match.group()
                break

        # Try to find time
        time_match = None
        for pattern in ICSUtils.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                time_match = match.group()
                break

        if not date_match:
            return None

        # Try to parse the date
        try:
            # Try common formats
            for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    date_obj = datetime.strptime(date_match, fmt)
                    break
                except ValueError:
                    continue
            else:
                # Default to today if we can't parse
                date_obj = datetime.now()
        except:
            date_obj = datetime.now()

        # If we have time, parse it
        if time_match:
            try:
                # Remove AM/PM for parsing
                time_clean = (
                    time_match.replace("AM", "")
                    .replace("PM", "")
                    .replace("am", "")
                    .replace("pm", "")
                    .strip()
                )
                if ":" in time_clean:
                    hour, minute = map(int, time_clean.split(":"))
                else:
                    hour = int(time_clean)
                    minute = 0

                # Adjust for PM
                if "PM" in time_match.upper() and hour != 12:
                    hour += 12
                elif "AM" in time_match.upper() and hour == 12:
                    hour = 0

                return date_obj.replace(hour=hour, minute=minute, second=0)
            except:
                pass

        # Default to 9 AM if no time found
        return date_obj.replace(hour=9, minute=0, second=0)

    @staticmethod
    def parse_ics_file(file_path: str) -> Dict[str, Any]:
        """Parse ICS file from path.

        Args:
            file_path: Path to .ics file

        Returns:
            Dict with event details
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ICSUtils.parse_ics(content)


# Testing command
if __name__ == "__main__":
    print("Testing ICS Utils...")

    # Test creation
    ics = ICSUtils.create_event(
        summary="Investor Meeting",
        start_time=datetime(2024, 2, 15, 10, 0),
        end_time=datetime(2024, 2, 15, 11, 0),
        description="Discuss funding round and cap table",
        location="Zoom",
        attendees=["investor@vc.com", "founder@startup.com"],
        organizer="assistant@linkup.com",
    )
    print("\nGenerated ICS:")
    print(ics[:200] + "...")

    # Test parsing
    parsed = ICSUtils.parse_ics(ics)
    print(f"\nParsed event: {parsed['summary']}")
    print(f"Start: {parsed['start']}")
    print(f"Attendees: {parsed['attendees']}")

    # Test keyword detection
    text1 = "Meeting with investor next Tuesday at 2 PM"
    text2 = "Please review the proposal"
    print(f"\nShould create event for '{text1}': {ICSUtils.should_create_event(text1)}")
    print(f"Should create event for '{text2}': {ICSUtils.should_create_event(text2)}")
