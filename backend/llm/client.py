import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_HOST
        self.model = settings.LLM_MODEL
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> dict:
        """
        Call Ollama chat API.
        Returns the full response dict.
        Raises httpx.TimeoutException or httpx.RequestError on network issues.
        """
        target_model = model or self.model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "think": False,           # disable qwen3 reasoning — major speedup
            "options": {
                "num_ctx": settings.LLM_NUM_CTX,
            },
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404 and target_model == self.model:
                    # Primary model not pulled; try fallback
                    logger.warning(
                        "Primary model %s not found, trying fallback %s",
                        self.model,
                        self.fallback_model,
                    )
                    return await self.chat(messages, tools, model=self.fallback_model)
                raise

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


ollama_client = OllamaClient()
