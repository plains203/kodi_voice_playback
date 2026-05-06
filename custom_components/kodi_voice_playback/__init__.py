"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

_LOGGER = logging.getLogger(__name__)

# Resolved at import time
_SENTENCES_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sentences", "en.yaml"
)

# Write a canary file the moment this module is imported
# This tells us whether HA is even loading the module at all
try:
    _canary = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loaded.txt")
    with open(_canary, "w") as _f:
        _f.write("module imported OK\n")
except Exception:
    pass


def get_domain():
    """Import DOMAIN lazily to catch any const.py errors explicitly."""
    from .const import DOMAIN
    return DOMAIN


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass, entry):
    """Set up entry."""
    DOMAIN = get_domain()
    hass.data.setdefault(DOMAIN, {})

    # Persistent notification — appears in HA UI bell icon, impossible to miss
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title":          "Kodi Voice Playback",
            "message":        f"async_setup_entry running for '{entry.data.get('kodi_name')}'",
            "notification_id": "kodi_vp_debug",
        },
        blocking=False,
    )

    # Write canary file to config dir so we know setup_entry ran
    canary = os.path.join(hass.config.config_dir, "kodi_vp_setup_ran.txt")
    try:
        with open(canary, "w") as f:
            f.write(f"setup_entry ran for {entry.data.get('kodi_name')}\n")
    except Exception as exc:
        _LOGGER.error("Kodi VP: could not write canary: %s", exc)

    # Copy sentences file
    dest = os.path.join(hass.config.config_dir, "custom_sentences", "en", "kodi_voice_playback.yaml")
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(_SENTENCES_SRC, dest)
        _LOGGER.warning("Kodi VP: sentences written to %s", dest)
    except Exception as exc:
        _LOGGER.error("Kodi VP: sentences copy failed: %s", exc)

    # Register intent handlers
    if not hass.data[DOMAIN].get("intents_registered"):
        try:
            from .intent import async_setup_intents
            await async_setup_intents(hass)
            hass.data[DOMAIN]["intents_registered"] = True
            _LOGGER.warning("Kodi VP: intent handlers registered")
        except Exception as exc:
            _LOGGER.error("Kodi VP: intent registration failed: %s", exc)

    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.warning("Kodi VP: setup complete for '%s'", entry.data.get("kodi_name"))
    return True


async def async_unload_entry(hass, entry):
    DOMAIN = get_domain()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    remaining = [k for k in hass.data[DOMAIN] if k != "intents_registered"]
    if not remaining:
        dest = os.path.join(hass.config.config_dir, "custom_sentences", "en", "kodi_voice_playback.yaml")
        try:
            os.remove(dest)
        except FileNotFoundError:
            pass
        hass.data[DOMAIN].pop("intents_registered", None)
    return True
