"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core            import HomeAssistant

from .const   import DOMAIN
from .intent  import async_setup_intents

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via configuration.yaml (not used — config flow only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Kodi instance from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Register the intent handler once (idempotent across multiple entries)
    if not hass.data[DOMAIN].get("intents_registered"):
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True
        _LOGGER.debug("KodiVoicePlayback intent handler registered")

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

    # If no instances left, clear the registered flag so it re-registers on next load
    remaining = [k for k in hass.data[DOMAIN] if k != "intents_registered"]
    if not remaining:
        hass.data[DOMAIN].pop("intents_registered", None)

    return True
