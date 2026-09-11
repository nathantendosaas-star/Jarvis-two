"""Chat Service — conversation and message management with async DB operations."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ..models.chat import Chat, Message


class ChatService:
    """Handles chat CRUD, message storage, and history retrieval."""

    @staticmethod
    async def create_chat(db: AsyncSession, project_id: str, title: str = "New Chat") -> Chat:
        chat = Chat(id=str(uuid.uuid4()), project_id=project_id, title=title)
        db.add(chat)
        await db.flush()
        return chat

    @staticmethod
    async def get_chats(db: AsyncSession, project_id: str) -> List[Chat]:
        result = await db.execute(
            select(Chat).where(Chat.project_id == project_id).order_by(desc(Chat.updated_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_chat(db: AsyncSession, chat_id: str) -> Optional[Chat]:
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.messages))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_chat(db: AsyncSession, chat_id: str) -> bool:
        chat = await db.get(Chat, chat_id)
        if chat:
            await db.delete(chat)
            return True
        return False

    @staticmethod
    async def add_message(
        db: AsyncSession,
        chat_id: str,
        role: str,
        content: str,
        token_count: int = 0,
        latency: float = 0.0,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=role,
            content=content,
            token_count=token_count,
            latency=latency,
        )
        db.add(msg)
        # Touch the parent chat's updated_at timestamp
        chat = await db.get(Chat, chat_id)
        if chat:
            chat.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return msg

    @staticmethod
    async def get_history(db: AsyncSession, chat_id: str, limit: int = 50) -> List[Dict[str, str]]:
        """Return the last N messages as simple dicts for prompt context assembly."""
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    @staticmethod
    async def update_chat_title(db: AsyncSession, chat_id: str, title: str):
        chat = await db.get(Chat, chat_id)
        if chat:
            chat.title = title
            await db.flush()
