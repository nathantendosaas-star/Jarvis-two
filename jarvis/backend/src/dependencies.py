"""FastAPI dependency injection — database sessions and singleton services."""

from .core.database import async_session
from .services.ai import AIService
from sqlalchemy.ext.asyncio import AsyncSession

_ai_service: AIService | None = None


async def get_db():
    """Yield a scoped async DB session; auto-commit on success, rollback on error."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_ai_service() -> AIService:
    """Return cached singleton AIService instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
