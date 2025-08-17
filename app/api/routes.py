# app/api/routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from uuid import UUID
import json

from app.api.dependencies import get_db
from app.utils.auth import verify_api_key
from app.services.chat_service import chat_service
from app.models.schemas import (
    SessionCreate, SessionResponse, SessionUpdate,
    MessageCreate, MessageResponse, PaginatedMessages,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


# Session endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
        session_data: SessionCreate,
        db: Session = Depends(get_db)
):
    try:
        return chat_service.create_session(db, session_data)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
        user_id: str = Query(..., description="User ID to filter sessions"),
        db: Session = Depends(get_db)
):
    try:
        return chat_service.get_sessions(db, user_id)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
        session_id: UUID,
        db: Session = Depends(get_db)
):
    try:
        session = chat_service.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")


@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
        session_id: UUID,
        update_data: SessionUpdate,
        db: Session = Depends(get_db)
):
    try:
        session = chat_service.update_session(db, session_id, update_data)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update session")


@router.patch("/sessions/{session_id}/favorite", response_model=SessionResponse)
async def toggle_favorite(
        session_id: UUID,
        db: Session = Depends(get_db)
):
    try:
        session = chat_service.toggle_favorite(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to toggle favorite")


@router.delete("/sessions/{session_id}")
async def delete_session(
        session_id: UUID,
        db: Session = Depends(get_db)
):
    try:
        if not chat_service.delete_session(db, session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete session")


# Message endpoints
@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_message(
        session_id: UUID,
        message_data: MessageCreate,
        db: Session = Depends(get_db)
):
    try:
        message = chat_service.add_message(db, session_id, message_data)
        if not message:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert JSON string back to dict for response if needed
        if message.context_metadata:
            try:
                message.context_metadata = json.loads(message.context_metadata)
            except:
                pass
        return message
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add message")


@router.get("/sessions/{session_id}/messages", response_model=PaginatedMessages)
async def get_messages(
        session_id: UUID,
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db)
):
    try:
        messages, total = chat_service.get_messages(db, session_id, skip, limit)

        # Convert JSON strings back to dicts
        for message in messages:
            if message.context_metadata:
                try:
                    message.context_metadata = json.loads(message.context_metadata)
                except:
                    pass

        return PaginatedMessages(
            messages=messages,
            total=total,
            skip=skip,
            limit=limit
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")
