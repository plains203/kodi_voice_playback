"""Config flow for Kodi Voice Playback."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const    import DOMAIN, CONF_KODI_NAME, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, DEFAULT_PORT
from .kodi_rpc import KodiRPC

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_KODI_NAME, description={"suggested_value": "lounge"}): str,
        vol.Required(CONF_HOST):                                                  str,
        vol.Optional(CONF_PORT,     default=DEFAULT_PORT):                        int,
        vol.Optional(CONF_USERNAME, default=""):                                  str,
        vol.Optional(CONF_PASSWORD, default=""):                                  str,
    }
)


async def _test_connection(hass, data: dict) -> str | None:
    """
    Try to reach Kodi. Returns None on success, or an error key string on failure.
    Uses GetTVShows as a more reliable test than JSONRPC.Ping (some Kodi builds
    don't respond to Ping correctly over HTTP).
    """
    kodi = KodiRPC(
        hass,
        data[CONF_HOST],
        data[CONF_PORT],
        data.get(CONF_USERNAME, ""),
        data.get(CONF_PASSWORD, ""),
    )
    try:
        # GetTVShows returns a valid result (even if empty list) when connected
        result = await kodi.call("VideoLibrary.GetTVShows", {"properties": ["title"]})
        _LOGGER.debug("Kodi connection test result: %s", result)
        # An empty dict means _rpc caught an exception — treat as failure
        if result is None:
            return "cannot_connect"
        return None
    except Exception as exc:
        _LOGGER.error("Kodi connection test exception: %s", exc)
        return "cannot_connect"


class KodiVoicePlaybackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            _LOGGER.debug("Config flow user input: %s", {
                k: v for k, v in user_input.items() if k != CONF_PASSWORD
            })
            error = await _test_connection(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                title = f"{user_input[CONF_KODI_NAME].title()} Kodi"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KodiVoicePlaybackOptionsFlow(config_entry)


class KodiVoicePlaybackOptionsFlow(config_entries.OptionsFlow):
    """Allow editing an existing Kodi instance."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            error = await _test_connection(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    self._entry, data=user_input
                )
                return self.async_create_entry(title="", data={})

        current = self._entry.data
        schema  = vol.Schema(
            {
                vol.Required(CONF_KODI_NAME, default=current.get(CONF_KODI_NAME, "")): str,
                vol.Required(CONF_HOST,      default=current.get(CONF_HOST, "")):       str,
                vol.Optional(CONF_PORT,      default=current.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_USERNAME,  default=current.get(CONF_USERNAME, "")):   str,
                vol.Optional(CONF_PASSWORD,  default=current.get(CONF_PASSWORD, "")):   str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
