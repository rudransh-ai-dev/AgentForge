import httpx
import json
import asyncio
from config import OLLAMA_URL, MODELS

# ── Fallback chains: if primary model fails, try fallback ──
FALLBACK_CHAIN = {
    "deepseek-coder:6.7b": "llama3:8b",
    "phi3:mini": "llama3:8b",
    "llama3:8b": "llama3:latest",
    "llama3:latest": "llama3:8b",
}

MAX_RETRIES = 2
RETRY_DELAY_BASE = 1.5  # seconds, exponential backoff


async def check_ollama_health() -> dict:
    """Check if Ollama is reachable and list available models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Ollama root endpoint
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"status": "connected", "models": models}
            return {"status": "error", "models": [], "detail": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "disconnected", "models": [], "detail": str(e)}


async def async_generate(model: str, prompt: str) -> str:
    """Generate with retry + fallback logic."""
    current_model = model
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OLLAMA_URL,
                    json={"model": current_model, "prompt": prompt, "stream": False},
                    timeout=120.0
                )
                data = response.json()
                if "error" in data:
                    raise Exception(f"Ollama Error: {data['error']}")
                return data["response"]
        except Exception as e:
            last_error = e
            print(f"⚠️  Attempt {attempt + 1} failed for model '{current_model}': {e}")

            # Try fallback model on first failure
            if attempt == 0 and current_model in FALLBACK_CHAIN:
                fallback = FALLBACK_CHAIN[current_model]
                print(f"🔄 Falling back: {current_model} → {fallback}")
                current_model = fallback

            # Exponential backoff before retry
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                await asyncio.sleep(delay)

    raise Exception(f"All {MAX_RETRIES + 1} attempts failed for model '{model}': {last_error}")


async def async_generate_stream(model: str, prompt: str):
    """Streaming generate with retry + fallback logic."""
    current_model = model
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    OLLAMA_URL,
                    json={"model": current_model, "prompt": prompt, "stream": True},
                    timeout=120.0
                ) as response:
                    if response.status_code != 200:
                        raise Exception(f"HTTP {response.status_code}")
                    
                    chunk_count = 0
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                text = data.get("response", "")
                                if text:
                                    chunk_count += 1
                                    yield text
                            except json.JSONDecodeError:
                                pass
                    
                    if chunk_count > 0:
                        return  # Success — exit retry loop
                    else:
                        raise Exception("Stream returned 0 chunks")

        except Exception as e:
            last_error = e
            print(f"⚠️  Stream attempt {attempt + 1} failed for '{current_model}': {e}")

            if attempt == 0 and current_model in FALLBACK_CHAIN:
                fallback = FALLBACK_CHAIN[current_model]
                print(f"🔄 Stream fallback: {current_model} → {fallback}")
                current_model = fallback

            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                await asyncio.sleep(delay)

    # If all retries failed, yield the error as final message
    yield f"\n\n⚠️ Error: All attempts failed for model '{model}'. Last error: {last_error}"
