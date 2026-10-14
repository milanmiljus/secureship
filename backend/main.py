import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from db.engine import AsyncSessionLocal
from routes.chat import router as chat_router
from routes.verify import router as verify_router
from routes.admin import router as admin_router
from services.session_store import session_store

logger = logging.getLogger(__name__)


async def _session_cleanup_loop() -> None:
    """Background task: evict expired sessions every 5 minutes (INV-05)."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        try:
            await session_store.cleanup_expired()
        except Exception:
            logger.exception("Error during session cleanup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # INV-12: Refuse to start with a half-configured Auth0 setup.
    # Both empty → dev mode (fine). Both set → production (fine).
    # One set without the other → misconfiguration → refuse to start.
    domain_set = bool(settings.AUTH0_DOMAIN)
    audience_set = bool(settings.AUTH0_AUDIENCE)
    if domain_set != audience_set:
        logger.error(
            "AUTH0 misconfiguration: AUTH0_DOMAIN=%r, AUTH0_AUDIENCE=%r. "
            "Both must be set together or both left empty (dev mode). Refusing to start.",
            settings.AUTH0_DOMAIN,
            settings.AUTH0_AUDIENCE,
        )
        sys.exit(1)

    if not domain_set:
        logger.warning("AUTH0_DOMAIN not set — running in dev mode (admin auth disabled)")

    logger.info("SecureShip API starting...")

    # INV-05: Start background session cleanup task
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="SecureShip API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(verify_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    db_reachable = False
    ollama_reachable = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_reachable = True
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
            ollama_reachable = resp.status_code == 200
    except Exception:
        pass

    return {"status": "ok", "db_reachable": db_reachable, "ollama_reachable": ollama_reachable}
