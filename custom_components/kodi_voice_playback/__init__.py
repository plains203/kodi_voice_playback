"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core            import HomeAssistant

from .const   import DOMAIN
from .intent  import async_setup_intents

_LOGGER = logging.getLogger(__name__)

# Destination inside the HA config dir — DefaultAgent always loads from here
_CUSTOM_SENTENCES_DIR  = "custom_sentences/en"
_CUSTOM_SENTENCES_FILE = "kodi_voice_playback.yaml"


def _install_sentences(config_dir: str) -> None:
    """Copy bundled sentences/en.yaml to custom_sentences/en/ (sync, run in executor)."""
    src = os.path.join(
        os.path.dirname(__file__), "sentences", "en.yaml"
    )
    dest_dir  = os.path.join(config_dir, _CUSTOM_SENTENCES_DIR)
    dest_file = os.path.join(dest_dir, _CUSTOM_SENTENCES_FILE)
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, dest_file)
    _LOGGER.debug("Installed sentences to %s", dest_file)


def _remove_sentences(config_dir: str) -> None:
    """Remove the installed sentences file (sync, run in executor)."""
    dest = os.path.join(config_dir, _CUSTOM_SENTENCES_DIR, _CUSTOM_SENTENCES_FILE)
    try:
        os.remove(dest)
        _LOGGER.debug("Removed sentences from %s", dest)
    except FileNotFoundError:
        pass


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Kodi instance from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get("intents_registered"):
        # Install sentences so HA's local Hassil engine picks them up
        await hass.async_add_executor_job(_install_sentences, hass.config.config_dir)

        # Register intent handlers
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True
        _LOGGER.info("Kodi Voice Playback: intent handlers and sentences registered")

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
        # Last instance removed — clean up sentences and registered flag
        await hass.async_add_executor_job(_remove_sentences, hass.config.config_dir)
        hass.data[DOMAIN].pop("intents_registered", None)
        _LOGGER.info("Kodi Voice Playback: unloaded, sentences removed")

    return True
