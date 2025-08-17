# app/services/chat_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.database import ChatSession, ChatMessage
from app.models.schemas import SessionCreate, SessionUpdate, MessageCreate
from typing import List, Optional
from uuid import UUID
import json


class ChatService:
    def create_session(self, db: Session, session_data: SessionCreate) -> ChatSession:
        try:
            db_session = ChatSession(**session_data.dict())
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            return db_session
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error creating session: {str(e)}")
            raise

    def get_sessions(self, db: Session, user_id: str) -> List[ChatSession]:
        try:
            return db.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).order_by(ChatSession.created_at.desc()).all()
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error getting sessions: {str(e)}")
            raise

    def get_session(self, db: Session, session_id: UUID) -> Optional[ChatSession]:
        try:
            return db.query(ChatSession).filter(ChatSession.id == session_id).first()
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error getting session {session_id}: {str(e)}")
            # Try to recover by creating a new transaction
            try:
                db.begin()
                return db.query(ChatSession).filter(ChatSession.id == session_id).first()
            except SQLAlchemyError as e2:
                print(f"Recovery attempt failed: {str(e2)}")
                return None

    def update_session(self, db: Session, session_id: UUID, update_data: SessionUpdate) -> Optional[ChatSession]:
        try:
            session = self.get_session(db, session_id)
            if session:
                for field, value in update_data.dict(exclude_unset=True).items():
                    setattr(session, field, value)
                db.commit()
                db.refresh(session)
            return session
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error updating session: {str(e)}")
            raise

    def toggle_favorite(self, db: Session, session_id: UUID) -> Optional[ChatSession]:
        try:
            session = self.get_session(db, session_id)
            if session:
                session.is_favorite = not session.is_favorite
                db.commit()
                db.refresh(session)
            return session
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error toggling favorite: {str(e)}")
            raise

    def delete_session(self, db: Session, session_id: UUID) -> bool:
        try:
            session = self.get_session(db, session_id)
            if session:
                db.delete(session)
                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error deleting session: {str(e)}")
            raise

    def add_message(self, db: Session, session_id: UUID, message_data: MessageCreate) -> Optional[ChatMessage]:
        try:
            # First try to get the session with error handling
            session = self.get_session(db, session_id)
            if not session:
                print(f"Session {session_id} not found")
                return None

            db_message = ChatMessage(
                session_id=session_id,
                sender=message_data.sender.lower(),  # Ensure lowercase
                content=message_data.content,
                context_metadata=json.dumps(message_data.context_metadata) if message_data.context_metadata else None
            )
            db.add(db_message)
            db.commit()
            db.refresh(db_message)
            return db_message
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error adding message: {str(e)}")
            raise

    def get_messages(self, db: Session, session_id: UUID, skip: int = 0, limit: int = 50) -> tuple[
        List[ChatMessage], int]:
        try:
            query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
            total = query.count()
            messages = query.order_by(ChatMessage.created_at).offset(skip).limit(limit).all()
            return messages, total
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error getting messages: {str(e)}")
            return [], 0

    def safe_session_check(self, db: Session, session_id: UUID) -> bool:
        """Safely check if a session exists without raising exceptions"""
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            return session is not None
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error checking session existence: {str(e)}")
            return False


chat_service = ChatService()