import json
import logging
import os
import uuid
from typing import AsyncIterator, Any

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class GigaChatLLM:
    def __init__(self, credentials: str | None = None, model: str = "GigaChat-2"):
        self.credentials = credentials or os.getenv("GIGACHAT_CREDENTIALS")
        self.model = model
        self.base_url = "https://api.giga.chat/v1"
        self.auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self._access_token = None

    async def warm(self, api_key: str = None):
        pass

    async def close(self):
        pass

    def _get_token(self) -> str:
        """Получает токен доступа через OAuth."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Bearer {self.credentials}"
        }
        response = requests.post(
            self.auth_url,
            headers=headers,
            data="scope=GIGACHAT_API_PERS",
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _ensure_token(self) -> str:
        if self._access_token is None:
            self._access_token = self._get_token()
        return self._access_token

    def _build_functions(self, tools: list[dict] | None) -> list[dict] | None:
        if not tools:
            return None
        functions = []
        for t in tools:
            func = t.get("function", t)
            functions.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {"type": "object", "properties": {}}),
            })
        return functions

    async def stream(
        self,
        system_prompt: str,
        history: list[dict],
        model: str,
        api_key: str,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[tuple[str, Any]]:
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h.get("content", "")})

        payload = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["functions"] = self._build_functions(tools)
            payload["function_call"] = "auto"

        token = self._ensure_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            verify=False,
            timeout=60
        )
        
        # Если токен протух (401), пробуем обновить один раз
        if response.status_code == 401:
            self._access_token = self._get_token()
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                verify=False,
                timeout=60
            )
        
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]

        if "function_call" in message:
            fc = message["function_call"]
            yield ("tool_calls", [{
                "name": fc["name"],
                "arguments": json.dumps(fc["arguments"], ensure_ascii=False),
            }])
            return

        content = message.get("content", "")
        for i in range(0, len(content), 8):
            yield ("text", content[i:i+8])