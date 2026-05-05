"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.const          import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core           import HomeAssistant, callback

from .const   import DOMAIN
from .intent  import async_setup_intents

_LOGGER = logging.getLogger(__name__)

_CUSTOM_SENTENCES_DIR  = "custom_sentences/en"
_CUSTOM_SENTENCES_FILE = "kodi_voice_playback.yaml"

# Resolve the source path once at import time — safe and reliable
_SENTENCES_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentences", "en.yaml")


def _sentences_dest(config_dir: str) -> str:
    return os.path.join(config_dir, _CUSTOM_SENTENCES_DIR, _CUSTOM_SENTENCES_FILE)


def _install_sentences_sync(config_dir: str, src: str) -> str:
    """Copy sentences file. src and dest passed explicitly — no module globals needed."""
    dest = _sentences_dest(config_dir)
    dest_dir = os.path.dirname(dest)

    _LOGGER.debug("Kodi Voice Playback: sentences src  = %s (exists=%s)", src, os.path.exists(src))
    _LOGGER.debug("Kodi Voice Playback: sentences dest = %s", dest)

    if not os.path.exists(src):
        _LOGGER.error(
            "Kodi Voice Playback: source sentences file not found at %s — "
            "the integration may be installed incorrectly.", src
        )
        return ""

    try:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(src, dest)
        _LOGGER.info("Kodi Voice Playback: sentences file written to %s", dest)
        return dest
    except Exception as exc:
        _LOGGER.error("Kodi Voice Playback: failed to write sentences file: %s", exc)
        return ""


def _remove_sentences_sync(config_dir: str) -> None:
    try:
        os.remove(_sentences_dest(config_dir))
        _LOGGER.debug("Kodi Voice Playback: sentences file removed")
    except FileNotFoundError:
        pass


async def _reload_default_agent(hass: HomeAssistant) -> None:
    """Directly reload the DefaultAgent so it picks up new custom_sentences files."""
    try:
        from homeassistant.components.conversation.default_agent import DefaultAgent

        # Try the agent ID used in recent HA versions first
        agent = None
        for agent_id in ("conversation.home_assistant", "homeassistant"):
            try:
                from homeassistant.components.conversation import async_get_agent
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
        _LOGGER.info(
            "Kodi Voice Playback: DefaultAgent reloaded for language '%s' — "
            "voice sentences are now active", language
        )

    except Exception as exc:
        _LOGGER.error(
            "Kodi Voice Playback: failed to reload DefaultAgent: %s. "
            "Restart HA to activate voice sentences.", exc
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Kodi instance from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get("intents_registered"):
        _LOGGER.info(
            "Kodi Voice Playback: first setup — installing sentences from %s",
            _SENTENCES_SRC,
        )

        # Write sentences file — pass src path explicitly, do NOT rely on __file__ in thread
        dest = await hass.async_add_executor_job(
            _install_sentences_sync, hass.config.config_dir, _SENTENCES_SRC
        )

        if not dest:
            _LOGGER.error(
                "Kodi Voice Playback: sentence installation failed — "
                "voice commands will not work. Check logs above for details."
            )
            # Continue loading so the integration itself still works
        
        # Register Python intent handlers
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True

        # Register manual reload service
        async def handle_reload_service(call) -> None:
            await _reload_default_agent(hass)

        hass.services.async_register(DOMAIN, "reload_sentences", handle_reload_service)

        # Reload DefaultAgent after HA has fully started
        if hass.is_running:
            hass.async_create_task(_reload_default_agent(hass))
        else:
            @callback
            def _on_started(event) -> None:
                hass.async_create_task(_reload_default_agent(hass))
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.info(
        "Kodi Voice Playback: loaded instance '%s' at %s:%s",
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
        _LOGGER.info("Kodi Voice Playback: unloaded, sentences removed")
    return True
