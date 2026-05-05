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


def _sentences_dest(config_dir: str) -> str:
    return os.path.join(config_dir, _CUSTOM_SENTENCES_DIR, _CUSTOM_SENTENCES_FILE)


def _install_sentences_sync(config_dir: str) -> str:
    src  = os.path.join(os.path.dirname(__file__), "sentences", "en.yaml")
    dest = _sentences_dest(config_dir)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def _remove_sentences_sync(config_dir: str) -> None:
    try:
        os.remove(_sentences_dest(config_dir))
    except FileNotFoundError:
        pass


async def _reload_default_agent(hass: HomeAssistant) -> None:
    """
    Force the DefaultAgent to reload its intents (including custom_sentences/).

    conversation.reload only reloads intent_script YAML — it does NOT rescan
    custom_sentences/. We must access the DefaultAgent directly.
    """
    try:
        from homeassistant.components.conversation import async_get_agent
        from homeassistant.components.conversation.default_agent import DefaultAgent

        agent = async_get_agent(hass, "conversation.home_assistant")
        if agent is None:
            # Older HA versions use a different ID
            agent = async_get_agent(hass, "homeassistant")

        if not isinstance(agent, DefaultAgent):
            _LOGGER.error(
                "Kodi Voice Playback: could not find DefaultAgent (got %s). "
                "Restart HA to activate voice sentences.", type(agent)
            )
            return

        # _async_load rescans custom_sentences/ and rebuilds the intent index
        language = hass.config.language or "en"
        await agent._async_load(language)
        _LOGGER.info(
            "Kodi Voice Playback: DefaultAgent reloaded for language '%s' — "
            "voice sentences are now active", language
        )

    except Exception as exc:
        _LOGGER.error(
            "Kodi Voice Playback: failed to reload DefaultAgent: %s. "
            "A full HA restart will activate the voice sentences.", exc
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Kodi instance from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get("intents_registered"):
        # 1. Write sentences file to custom_sentences/en/ so it loads on next boot too
        dest = await hass.async_add_executor_job(
            _install_sentences_sync, hass.config.config_dir
        )
        _LOGGER.info("Kodi Voice Playback: sentences written to %s", dest)

        # 2. Register Python intent handlers
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True

        # 3. Register a manual service for users to force a reload if needed
        async def handle_reload_service(call) -> None:
            await _reload_default_agent(hass)

        hass.services.async_register(DOMAIN, "reload_sentences", handle_reload_service)

        # 4. Reload DefaultAgent after HA finishes starting so it picks up
        #    the new sentences file we just wrote
        if hass.is_running:
            hass.async_create_task(_reload_default_agent(hass))
        else:
            @callback
            def _on_started(event) -> None:
                hass.async_create_task(_reload_default_agent(hass))

            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.info(
        "Kodi Voice Playback: loaded '%s' at %s:%s",
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
