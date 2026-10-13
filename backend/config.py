from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://secureship:secureship@postgres:5432/secureship"
    OLLAMA_HOST: str = "http://host.docker.internal:11434"
    LLM_MODEL: str = "qwen3:8b"
    LLM_FALLBACK_MODEL: str = "llama3.2:3b"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_NUM_CTX: int = 4096       # context window — smaller = faster inference
    LLM_MAX_HISTORY: int = 10     # max message turns kept in memory per session
    SESSION_TTL_MINUTES: int = 30
    CODE_EXPIRY_MINUTES: int = 10
    MAX_CODE_ATTEMPTS: int = 3
    AUTH0_DOMAIN: str = ""
    AUTH0_AUDIENCE: str = ""
    AUTH0_CLIENT_ID: str = ""
    MAX_TOOL_ITERATIONS: int = 8

    class Config:
        env_file = ".env"


settings = Settings()
