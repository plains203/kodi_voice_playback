"""Intent handlers for Kodi Voice Playback."""
from __future__ import annotations

import logging

from homeassistant.core    import HomeAssistant
from homeassistant.helpers import intent

from .const    import DOMAIN, CONF_KODI_NAME, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, INTENT_TYPE, MOVIE_INTENT_TYPE
from .kodi_rpc import KodiRPC
from .match    import best_show_match, extract_device_from_show_name

_LOGGER = logging.getLogger(__name__)


async def async_setup_intents(hass: HomeAssistant) -> None:
    intent.async_register(hass, KodiPlayNextEpisodeHandler())
    intent.async_register(hass, KodiPlayMovieHandler())


def _find_entry(entries, device_hint: str):
    if not device_hint:
        return entries[0]
    hint = device_hint.lower().replace("kodi", "").strip()
    for e in entries:
        n = e.data.get(CONF_KODI_NAME, "").lower()
        if hint in n or n in hint:
            return e
    hint_words = set(hint.split())
    best_score, best = 0.0, None
    for e in entries:
        name_words = set(e.data.get(CONF_KODI_NAME, "").lower().split())
        score = len(hint_words & name_words) / max(len(hint_words), 1)
        if score > best_score:
            best_score, best = score, e
    return best if (best and best_score > 0) else entries[0]


def _get_kodi(hass, entry) -> KodiRPC:
    return KodiRPC(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_USERNAME, ""),
        entry.data.get(CONF_PASSWORD, ""),
    )


def _no_instances_speech():
    return (
        "No Kodi instances are configured. "
        "Add one via Settings, Devices and Services, Kodi Voice Playback."
    )


class KodiPlayNextEpisodeHandler(intent.IntentHandler):
    intent_type = INTENT_TYPE

    # No slot_schema — non_empty_string was removed in newer HA versions
    # Slots are validated manually inside async_handle instead

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass        = intent_obj.hass
        slots       = intent_obj.slots
        show_name   = slots.get("show_name",   {}).get("value", "").strip()
        kodi_device = slots.get("kodi_device", {}).get("value", "").strip()
        response    = intent_obj.create_response()

        if not show_name:
            response.async_set_speech("What show would you like to watch?")
            return response

        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            response.async_set_speech(_no_instances_speech())
            return response

        known_names = [e.data.get(CONF_KODI_NAME, "") for e in entries]
        if not kodi_device:
            show_name, kodi_device = extract_device_from_show_name(show_name, known_names)

        _LOGGER.debug("KodiPlayNextEpisode: show='%s' device='%s'", show_name, kodi_device)

        entry = _find_entry(entries, kodi_device)
        name  = entry.data.get(CONF_KODI_NAME, entry.data[CONF_HOST])
        kodi  = _get_kodi(hass, entry)

        shows = await kodi.get_tv_shows()
        if not shows:
            response.async_set_speech(f"No TV shows found in Kodi on {name}. Try running a library scan.")
            return response

        matched = best_show_match(shows, show_name)
        if not matched:
            response.async_set_speech(f"I couldn't find {show_name} in your Kodi library.")
            return response

        show_title = matched["title"]
        show_id    = matched["tvshowid"]

        episode = await kodi.get_next_episode(show_id)
        if not episode:
            response.async_set_speech(f"You've watched every episode of {show_title}.")
            return response

        season   = episode["season"]
        ep_num   = episode["episode"]
        ep_title = episode["title"]
        ep_file  = episode["file"]
        resume_s = episode.get("resume", {}).get("position", 0)

        await kodi.play(ep_file, resume=resume_s > 0)

        if resume_s > 0:
            mins     = int(resume_s // 60)
            secs     = int(resume_s  % 60)
            time_str = f"{mins} minute{'s' if mins != 1 else ''}"
            if secs:
                time_str += f" and {secs} seconds"
            speech = (
                f"Resuming {show_title}, Season {season} Episode {ep_num}, "
                f"{ep_title}, from {time_str} in."
            )
        else:
            speech = f"Playing {show_title}, Season {season} Episode {ep_num}, {ep_title}."

        response.async_set_speech(speech)
        return response


class KodiPlayMovieHandler(intent.IntentHandler):
    intent_type = MOVIE_INTENT_TYPE

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass        = intent_obj.hass
        slots       = intent_obj.slots
        movie_name  = slots.get("movie_name",  {}).get("value", "").strip()
        kodi_device = slots.get("kodi_device", {}).get("value", "").strip()
        response    = intent_obj.create_response()

        if not movie_name:
            response.async_set_speech("What movie would you like to watch?")
            return response

        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            response.async_set_speech(_no_instances_speech())
            return response

        known_names = [e.data.get(CONF_KODI_NAME, "") for e in entries]
        if not kodi_device:
            movie_name, kodi_device = extract_device_from_show_name(movie_name, known_names)

        _LOGGER.debug("KodiPlayMovie: movie='%s' device='%s'", movie_name, kodi_device)

        entry = _find_entry(entries, kodi_device)
        name  = entry.data.get(CONF_KODI_NAME, entry.data[CONF_HOST])
        kodi  = _get_kodi(hass, entry)

        movies = await kodi.get_movies()
        if not movies:
            response.async_set_speech(f"No movies found in Kodi on {name}. Try running a library scan.")
            return response

        matched = best_show_match(movies, movie_name)
        if not matched:
            response.async_set_speech(f"I couldn't find the movie {movie_name} in your Kodi library.")
            return response

        movie_title = matched["title"]
        movie_file  = matched["file"]
        resume_s    = matched.get("resume", {}).get("position", 0)

        await kodi.play(movie_file, resume=resume_s > 0)

        if resume_s > 0:
            mins     = int(resume_s // 60)
            secs     = int(resume_s  % 60)
            time_str = f"{mins} minute{'s' if mins != 1 else ''}"
            if secs:
                time_str += f" and {secs} seconds"
            speech = f"Resuming {movie_title} from {time_str} in."
        else:
            speech = f"Playing {movie_title}."

        response.async_set_speech(speech)
        return response
