import logging
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SecureShip API starting...")
    yield


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
