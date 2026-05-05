"""Async Kodi JSON-RPC client using HA's shared aiohttp session."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class KodiRPC:
    """Thin async wrapper around the Kodi JSON-RPC HTTP API."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
    ) -> None:
        self._hass = hass
        self._url  = f"http://{host}:{port}/jsonrpc"
        self._auth = (username, password) if username else None

    async def call(self, method: str, params: dict | None = None) -> dict[str, Any] | None:
        """
        Make a JSON-RPC call.
        Returns the result dict on success, or None on any error.
        Callers should treat None as a connection/RPC failure.
        """
        session = async_get_clientsession(self._hass)
        payload = {
            "jsonrpc": "2.0",
            "id":      1,
            "method":  method,
            "params":  params or {},
        }
        kwargs: dict[str, Any] = {"json": payload, "timeout": 10}
        if self._auth:
            from aiohttp import BasicAuth
            kwargs["auth"] = BasicAuth(*self._auth)

        try:
            async with session.post(self._url, **kwargs) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                if "error" in data:
                    _LOGGER.error("Kodi RPC error for %s: %s", method, data["error"])
                    return None
                return data.get("result", {})
        except Exception as exc:
            _LOGGER.error("Kodi HTTP error calling %s at %s: %s", method, self._url, exc)
            return None

    async def get_tv_shows(self) -> list[dict]:
        result = await self.call("VideoLibrary.GetTVShows", {"properties": ["title"]})
        return result.get("tvshows", []) if result is not None else []

    async def get_movies(self) -> list[dict]:
        result = await self.call("VideoLibrary.GetMovies", {"properties": ["title", "file", "resume"]})
        return result.get("movies", []) if result is not None else []

    async def get_next_episode(self, show_id: int) -> dict | None:
        """Return the next unplayed episode, preferring in-progress ones."""
        result = await self.call(
            "VideoLibrary.GetEpisodes",
            {
                "tvshowid":   show_id,
                "properties": ["title", "season", "episode", "playcount", "file", "resume"],
                "filter":     {"field": "playcount", "operator": "lessthan", "value": "1"},
                "sort":       {"method": "episode", "order": "ascending"},
            },
        )
        if result is None:
            return None
        episodes = result.get("episodes", [])
        if not episodes:
            return None
        in_progress = [ep for ep in episodes if ep.get("resume", {}).get("position", 0) > 0]
        return in_progress[0] if in_progress else episodes[0]

    async def play(self, file_path: str, resume: bool = False) -> None:
        await self.call(
            "Player.Open",
            {"item": {"file": file_path}, "options": {"resume": resume}},
        )
