import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Protocol, Optional
import uuid

from config import settings
from domain.session import Session, SessionState

logger = logging.getLogger(__name__)


class SessionStoreProtocol(Protocol):
    async def create(self, chat_session_db_id: str) -> Session: ...
    async def get(self, session_id: str) -> Optional[Session]: ...
    async def save(self, session: Session) -> None: ...
    async def delete(self, session_id: str) -> None: ...


class InMemorySessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create(self, chat_session_db_id: str) -> Session:
        session = Session(
            session_id=str(uuid.uuid4()),
            chat_session_db_id=chat_session_db_id,
        )
        async with self._lock:
            self._sessions[session.session_id] = session
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        async with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return None
        # Check TTL
        ttl = timedelta(minutes=settings.SESSION_TTL_MINUTES)
        if datetime.now(timezone.utc) - session.last_active_at > ttl:
            await self.delete(session_id)
            return None
        return session

    async def save(self, session: Session) -> None:
        session.last_active_at = datetime.now(timezone.utc)
        async with self._lock:
            self._sessions[session.session_id] = session

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def cleanup_expired(self) -> int:
        """
        Remove all sessions that have exceeded SESSION_TTL_MINUTES of inactivity.
        Returns the number of sessions evicted.
        Called by the background task in main.py every 5 minutes.
        """
        ttl = timedelta(minutes=settings.SESSION_TTL_MINUTES)
        now = datetime.now(timezone.utc)
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session.last_active_at > ttl
        ]
        async with self._lock:
            for sid in expired:
                self._sessions.pop(sid, None)
        if expired:
            logger.info("Session cleanup: evicted %d expired session(s)", len(expired))
        return len(expired)


# Singleton — replaced by Redis implementation later without changing any other code
session_store = InMemorySessionStore()
