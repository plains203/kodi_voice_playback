"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.const          import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core           import HomeAssistant, callback

from .const  import DOMAIN
from .intent import async_setup_intents

_LOGGER = logging.getLogger(__name__)

_CUSTOM_SENTENCES_DIR  = "custom_sentences/en"
_CUSTOM_SENTENCES_FILE = "kodi_voice_playback.yaml"

# Resolved once at import time — safe to use from any thread
_SENTENCES_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sentences", "en.yaml"
)


def _sentences_dest(config_dir: str) -> str:
    return os.path.join(config_dir, _CUSTOM_SENTENCES_DIR, _CUSTOM_SENTENCES_FILE)


def _install_sentences_sync(config_dir: str, src: str) -> str:
    """Always copy the sentences file. Returns dest path, or empty string on failure."""
    dest     = _sentences_dest(config_dir)
    dest_dir = os.path.dirname(dest)

    _LOGGER.warning(
        "Kodi Voice Playback [install]: src=%s exists=%s dest=%s",
        src, os.path.exists(src), dest,
    )

    if not os.path.exists(src):
        _LOGGER.error(
            "Kodi Voice Playback: source sentences file not found at %s — "
            "the integration may not be installed correctly.", src
        )
        return ""

    try:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(src, dest)
        _LOGGER.warning(
            "Kodi Voice Playback [install]: successfully wrote %s", dest
        )
        return dest
    except Exception as exc:
        _LOGGER.error(
            "Kodi Voice Playback: failed to write sentences file to %s: %s",
            dest, exc,
        )
        return ""


def _remove_sentences_sync(config_dir: str) -> None:
    try:
        os.remove(_sentences_dest(config_dir))
    except FileNotFoundError:
        pass


async def _reload_default_agent(hass: HomeAssistant) -> None:
    """Tell the DefaultAgent to rescan custom_sentences/."""
    try:
        from homeassistant.components.conversation.default_agent import DefaultAgent
        from homeassistant.components.conversation import async_get_agent

        agent = None
        for agent_id in ("conversation.home_assistant", "homeassistant"):
            try:
                agent = async_get_agent(hass, agent_id)
                if agent is not None:
                    break
            except Exception:
                pass

        if not isinstance(agent, DefaultAgent):
            _LOGGER.error(
                "Kodi Voice Playback: DefaultAgent not found (got %s). "
                "Restart HA to activate voice sentences.", type(agent)
            )
            return

        language = hass.config.language or "en"
        await agent._async_load(language)
        _LOGGER.warning(
            "Kodi Voice Playback: DefaultAgent reloaded for '%s' — sentences active",
            language,
        )

    except Exception as exc:
        _LOGGER.error(
            "Kodi Voice Playback: DefaultAgent reload failed: %s. "
            "Restart HA to activate voice sentences.", exc
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # ── Always copy the sentences file on every setup ─────────────────────────
    # Do NOT gate this on intents_registered — the file must exist on disk
    # regardless of whether handlers are already registered in memory.
    _LOGGER.warning(
        "Kodi Voice Playback: async_setup_entry called for '%s', installing sentences",
        entry.data.get("kodi_name"),
    )
    dest = await hass.async_add_executor_job(
        _install_sentences_sync, hass.config.config_dir, _SENTENCES_SRC
    )

    # ── Register intent handlers and services only once ───────────────────────
    if not hass.data[DOMAIN].get("intents_registered"):
        await async_setup_intents(hass)

        async def handle_reload_service(call) -> None:
            await _reload_default_agent(hass)

        hass.services.async_register(DOMAIN, "reload_sentences", handle_reload_service)
        hass.data[DOMAIN]["intents_registered"] = True
        _LOGGER.warning("Kodi Voice Playback: intent handlers registered")

    # ── Reload DefaultAgent so sentences are active without a restart ─────────
    if dest:
        if hass.is_running:
            hass.async_create_task(_reload_default_agent(hass))
        else:
            @callback
            def _on_started(event) -> None:
                hass.async_create_task(_reload_default_agent(hass))
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.warning(
        "Kodi Voice Playback: setup complete for '%s' at %s:%s",
        entry.data.get("kodi_name"),
        entry.data.get("host"),
        entry.data.get("port"),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    remaining = [k for k in hass.data[DOMAIN] if k != "intents_registered"]
    if not remaining:
        await hass.async_add_executor_job(_remove_sentences_sync, hass.config.config_dir)
        hass.data[DOMAIN].pop("intents_registered", None)
    return True
