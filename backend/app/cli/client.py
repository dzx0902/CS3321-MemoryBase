from __future__ import annotations

from typing import Any, Protocol

import httpx

from .config import CliConfig


class MemoryBaseClientError(Exception):
    pass


class MemoryBaseServerError(Exception):
    pass


class MemoryBaseClient(Protocol):
    def health_detail(
        self, *, workspace: str | None = None, agent: str | None = None
    ) -> dict[str, Any]:
        ...

    def register_agent(
        self, *, workspace: str, name: str, agent_type: str
    ) -> dict[str, Any]:
        ...

    def recall(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def context_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class HttpMemoryBaseClient:
    def __init__(self, api_base_url: str) -> None:
        self._api_base_url = api_base_url.rstrip("/")

    def health_detail(
        self, *, workspace: str | None = None, agent: str | None = None
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {"workspace": workspace, "agent": agent}.items()
            if value
        }
        return self._request("GET", "/api/health/detail", params=params)

    def register_agent(
        self, *, workspace: str, name: str, agent_type: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/agents/register",
            json={"workspace": workspace, "name": name, "agent_type": agent_type},
        )

    def recall(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/recall", json=payload)

    def context_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/recall/context-pack", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self._api_base_url}{path}"
        try:
            response = httpx.request(method, url, timeout=10.0, **kwargs)
        except httpx.RequestError as exc:
            raise MemoryBaseServerError(str(exc)) from exc

        if 400 <= response.status_code < 500:
            raise MemoryBaseClientError(response.text)
        if response.status_code >= 500:
            raise MemoryBaseServerError(response.text)
        payload = response.json()
        if not isinstance(payload, dict):
            raise MemoryBaseServerError("MemoryBase API returned a non-object response.")
        return payload


def build_client(config: CliConfig, *, local: bool = False) -> MemoryBaseClient:
    if local:
        raise MemoryBaseClientError("--local is reserved for dev/CI and is not implemented in PR1.")
    return HttpMemoryBaseClient(config.api_base_url)
