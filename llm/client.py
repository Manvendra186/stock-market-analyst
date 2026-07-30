"""
LLM Client - Connects to local Qwen3.6 27B model
Works with any OpenAI-compatible API (Ollama, LM Studio, vLLM, etc.)
"""
import httpx
import logging
from config import LLM_BASE_URL, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


async def chat(system_prompt: str, user_message: str) -> str:
    """Send a chat completion request to the local LLM."""
    url = f"{LLM_BASE_URL}/v1/chat/completions"

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    headers = {"Content-Type": "application/json"}

    logger.info(f"Sending request to LLM at {url}")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            result = data["choices"][0]["message"]["content"]
            logger.info(f"Received response ({len(result)} chars)")
            return result
        except httpx.ConnectError:
            logger.error(f"Cannot connect to LLM at {LLM_BASE_URL}. Is it running?")
            return f"⚠️ LLM service unavailable. Please ensure your local model is running at {LLM_BASE_URL}"
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            return f"⚠️ LLM error ({e.response.status_code}). Check your model server."
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected LLM response format: {e}")
            return "⚠️ Unexpected response from LLM. Please check logs."
