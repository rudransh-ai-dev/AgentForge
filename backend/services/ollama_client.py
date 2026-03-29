import httpx
import json
from config import OLLAMA_URL

async def async_generate(model: str, prompt: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                OLLAMA_URL,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120.0
            )
            data = response.json()
            if "error" in data:
                raise Exception(f"Ollama Error: {data['error']}")
            return data["response"]
        except Exception as e:
            raise Exception(f"Failed to generate: {str(e)}")

async def async_generate_stream(model: str, prompt: str):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": True},
            timeout=120.0
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield data.get("response", "")
                    except json.JSONDecodeError:
                        pass
