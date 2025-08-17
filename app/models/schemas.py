# app/models/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class SenderType(str, Enum):
    user = "user"
    assistant = "assistant"


# Session Schemas
class SessionCreate(BaseModel):
    user_id: str
    title: str = "New Chat"


class SessionUpdate(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    id: UUID
    user_id: str
    title: str
    is_favorite: bool
    has_documents: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    sender: SenderType
    content: str
    context_metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    sender: SenderType
    content: str
    context_metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Pagination
class PaginatedMessages(BaseModel):
    messages: List[MessageResponse]
    total: int
    skip: int
    limit: int
