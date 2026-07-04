from __future__ import annotations

import json
from http.client import RemoteDisconnected
from json import JSONDecodeError
from typing import Any
from urllib import error, request

from backend.schemas.model_settings_schema import ModelSettings


class OpenAICompatibleClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings

    def chat(
        self,
        system_prompt: str,
        user_text: str,
        image_data_url: str | None = None,
        image_data_urls: list[str] | None = None,
    ) -> str:
        if not self.settings.base_url or not self.settings.model or not self.settings.api_key:
            raise ValueError("Model settings are incomplete. Please configure base_url, api_key, and model.")

        normalized_images = list(image_data_urls or [])
        if image_data_url:
            normalized_images.insert(0, image_data_url)

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": self._build_user_content(user_text=user_text, image_data_urls=normalized_images),
                },
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "stream": False,
        }
        http_request = request.Request(
            url=f"{self.settings.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )

        body = ""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                with request.urlopen(http_request, timeout=self.settings.timeout) as response:
                    body = response.read().decode("utf-8", errors="replace")
                break
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"Model request failed with HTTP {exc.code}: {detail or exc.reason}") from exc
            except error.URLError as exc:
                raise RuntimeError(f"Model request failed: {exc.reason}") from exc
            except (RemoteDisconnected, ConnectionResetError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt == 1:
                    raise RuntimeError(
                        "Model service closed the connection before returning a complete response. "
                        "This usually means the upstream OpenAI-compatible proxy generated output but terminated the HTTP connection early. "
                        "Please retry, increase timeout, or switch to a more stable base_url/provider."
                    ) from exc

        if not body.strip():
            if last_error is not None:
                raise RuntimeError(
                    "Model response body is empty after the upstream connection was interrupted. "
                    "Please check whether the provider supports non-streaming /chat/completions responses."
                ) from last_error
            raise RuntimeError("Model response body is empty. Check whether base_url points to a valid OpenAI-compatible /chat/completions service.")

        try:
            payload = json.loads(body)
        except JSONDecodeError as exc:
            snippet = body[:300].replace("\n", " ").replace("\r", " ")
            raise RuntimeError(f"Model response is not valid JSON: {snippet}") from exc
        return self._extract_text(payload)

    def test_connection(self) -> str:
        return self.chat(system_prompt="You are a concise assistant.", user_text="Return exactly: OK")

    def _build_user_content(self, user_text: str, image_data_urls: list[str] | None = None) -> Any:
        if self.settings.vision_enabled and image_data_urls:
            content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
            for image_url in image_data_urls:
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            return content
        return user_text

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Model response does not contain choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_chunks = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_chunks.append(str(item.get("text", "")))
            return "\n".join(chunk for chunk in text_chunks if chunk)
        raise RuntimeError("Model response content format is unsupported.")
