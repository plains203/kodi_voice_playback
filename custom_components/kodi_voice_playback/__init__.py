"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries  import ConfigEntry
from homeassistant.core            import HomeAssistant, callback
from homeassistant.helpers.event   import async_call_later
from homeassistant.helpers.start   import async_at_start

from .const   import DOMAIN
from .intent  import async_setup_intents

_LOGGER = logging.getLogger(__name__)

_CUSTOM_SENTENCES_DIR  = "custom_sentences/en"
_CUSTOM_SENTENCES_FILE = "kodi_voice_playback.yaml"


def _install_sentences(config_dir: str) -> str:
    """Copy bundled sentences/en.yaml to custom_sentences/en/. Returns dest path."""
    src       = os.path.join(os.path.dirname(__file__), "sentences", "en.yaml")
    dest_dir  = os.path.join(config_dir, _CUSTOM_SENTENCES_DIR)
    dest_file = os.path.join(dest_dir, _CUSTOM_SENTENCES_FILE)
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, dest_file)
    return dest_file


def _remove_sentences(config_dir: str) -> None:
    dest = os.path.join(config_dir, _CUSTOM_SENTENCES_DIR, _CUSTOM_SENTENCES_FILE)
    try:
        os.remove(dest)
        _LOGGER.debug("Removed sentences: %s", dest)
    except FileNotFoundError:
        pass


async def _reload_conversation(hass: HomeAssistant) -> None:
    """Reload the conversation component so it picks up our sentences file."""
    try:
        await hass.services.async_call("conversation", "reload", blocking=True)
        _LOGGER.info("Kodi Voice Playback: conversation reloaded — sentences now active")
    except Exception as exc:
        _LOGGER.error(
            "Kodi Voice Playback: failed to reload conversation (%s). "
            "Sentences will only be active after the next HA restart. "
            "You can also trigger this manually via Developer Tools → Services → conversation.reload",
            exc,
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Kodi instance from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get("intents_registered"):
        # 1. Copy sentences file to custom_sentences/en/
        dest = await hass.async_add_executor_job(_install_sentences, hass.config.config_dir)
        _LOGGER.info("Kodi Voice Playback: sentences installed to %s", dest)

        # 2. Register Python intent handlers
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True

        # 3. Reload conversation — but AFTER HA has fully started, so the
        #    service is available and the reload takes effect cleanly.
        #    async_at_start fires immediately if HA is already running (e.g.
        #    user added integration via UI), or waits for startup to complete.
        @callback
        def _on_ha_started(hass: HomeAssistant) -> None:
            hass.async_create_task(_reload_conversation(hass))

        async_at_start(hass, _on_ha_started)

    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.info(
        "Kodi Voice Playback: loaded instance '%s' at %s:%s",
        entry.data.get("kodi_name"),
        entry.data.get("host"),
        entry.data.get("port"),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)

    remaining = [k for k in hass.data[DOMAIN] if k != "intents_registered"]
    if not remaining:
        await hass.async_add_executor_job(_remove_sentences, hass.config.config_dir)
        hass.data[DOMAIN].pop("intents_registered", None)
        _LOGGER.info("Kodi Voice Playback: unloaded, sentences removed")

    return True
