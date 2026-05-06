"""Kodi Voice Playback — voice intent integration."""
from __future__ import annotations

import logging
import os
import shutil

_LOGGER = logging.getLogger(__name__)

_SENTENCES_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sentences", "en.yaml"
)
_SENTENCES_DEST_REL = os.path.join("custom_sentences", "en", "kodi_voice_playback.yaml")


def _install_sentences_sync(config_dir: str) -> str:
    """Run in executor — all file I/O here, none in the event loop."""
    dest = os.path.join(config_dir, _SENTENCES_DEST_REL)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(_SENTENCES_SRC, dest)
    return dest


def _remove_sentences_sync(config_dir: str) -> None:
    """Run in executor."""
    try:
        os.remove(os.path.join(config_dir, _SENTENCES_DEST_REL))
    except FileNotFoundError:
        pass


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass, entry):
    from .const  import DOMAIN
    from .intent import async_setup_intents

    hass.data.setdefault(DOMAIN, {})

    # All file I/O in executor — fixes the blocking-call warnings
    dest = await hass.async_add_executor_job(_install_sentences_sync, hass.config.config_dir)
    _LOGGER.warning("Kodi Voice Playback: sentences written to %s", dest)

    if not hass.data[DOMAIN].get("intents_registered"):
        await async_setup_intents(hass)
        hass.data[DOMAIN]["intents_registered"] = True
        _LOGGER.warning("Kodi Voice Playback: intent handlers registered")

    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.warning("Kodi Voice Playback: setup complete for '%s'", entry.data.get("kodi_name"))
    return True


async def async_unload_entry(hass, entry):
    from .const import DOMAIN
    hass.data[DOMAIN].pop(entry.entry_id, None)
    remaining = [k for k in hass.data[DOMAIN] if k != "intents_registered"]
    if not remaining:
        await hass.async_add_executor_job(_remove_sentences_sync, hass.config.config_dir)
        hass.data[DOMAIN].pop("intents_registered", None)
    return True
