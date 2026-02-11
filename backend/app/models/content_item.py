"""Content item models for unified content storage."""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Source type enumeration for content categorization."""
    PDF = "pdf"
    EMAIL = "email"
    MESSAGE = "message"
    RESEARCH = "research"
    NOTE = "note"


class ContentItem(BaseModel):
    """Unified content item model for all stored content.
    
    Supports PDFs, emails, messages, research results, and notes with
    full metadata and vector embedding tracking.
    """
    id: str = Field(..., description="Unique identifier (UUID)")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    source_type: SourceType = Field(..., description="Type of content source")
    title: str = Field(..., description="Content title or subject")
    content: str = Field(..., description="Main content text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    file_path: Optional[str] = Field(None, description="Path to original file if applicable")
    sender: Optional[str] = Field(None, description="Sender identifier (for emails/messages)")
    recipients: Optional[List[str]] = Field(None, description="List of recipients (for emails/messages)")
    timestamp: Optional[datetime] = Field(None, description="Original timestamp of content")
    thread_id: Optional[str] = Field(None, description="Thread/conversation identifier")
    embedded_at: Optional[datetime] = Field(None, description="When content was embedded in vector store")
    embedding_id: Optional[int] = Field(None, description="Vector store embedding ID")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        use_enum_values = True
