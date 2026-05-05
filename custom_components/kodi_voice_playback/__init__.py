"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core           import HomeAssistant

from .const  import DOMAIN
from .intent import async_setup_intents

_LOGGER = logging.getLogger(__name__)

_SENTENCES_SRC  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentences", "en.yaml")
_SENTENCES_DEST = os.path.join("custom_sentences", "en", "kodi_voice_playback.yaml")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.warning("Kodi Voice Playback: async_setup_entry called for '%s'", entry.data.get("kodi_name"))

    # Copy sentences file on every setup so it's always present
    dest = os.path.join(hass.config.config_dir, _SENTENCES_DEST)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(_SENTENCES_SRC, dest)
        _LOGGER.warning("Kodi Voice Playback: sentences written to %s", dest)
    except Exception as exc:
        _LOGGER.error(
            "Kodi Voice Playback: could not write sentences file to %s: %s — "
            "manually copy custom_sentences/en/kodi_voice_playback.yaml from the zip "
            "to %s", dest, exc, os.path.dirname(dest)
        )

    # Register intent handlers once
    if not hass.data[DOMAIN].get("intents_registered"):
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True
        _LOGGER.warning("Kodi Voice Playback: intent handlers registered")

    hass.data[DOMAIN][entry.entry_id] = entry.data
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    remaining = [k for k in hass.data[DOMAIN] if k != "intents_registered"]
    if not remaining:
        dest = os.path.join(hass.config.config_dir, _SENTENCES_DEST)
        try:
            os.remove(dest)
        except FileNotFoundError:
            pass
        hass.data[DOMAIN].pop("intents_registered", None)
    return True
