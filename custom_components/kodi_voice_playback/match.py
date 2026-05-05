"""Fuzzy show-title matching for Kodi Voice Playback intent."""
from __future__ import annotations

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to",
    "is", "it", "its", "my", "our", "your", "their",
}


def best_show_match(shows: list[dict], query: str) -> dict | None:
    """
    Return the best-matching show dict from *shows* for the given *query*,
    or None if nothing scores above the minimum threshold.

    Scoring (higher = better match):
      +1.0  all significant query words appear in the title
      +0–0.5 significant word overlap ratio
      +0–0.5 title length is close to query length (penalises "Lost in Space"
              when the user just said "Lost")
      +0.2  query is a substring of the title
    """
    q       = query.lower().strip()
    q_words = set(q.split())
    q_sig   = q_words - _STOP_WORDS or q_words   # fallback if all stop words

    best_score, best = 0.0, None

    for show in shows:
        title   = show["title"].lower()
        t_words = set(title.split())
        t_sig   = t_words - _STOP_WORDS or t_words

        sig_overlap = len(q_sig & t_sig)

        # Must share at least one significant word, or be a substring match
        if sig_overlap == 0 and q not in title:
            continue

        # Exact match — return immediately
        if title == q:
            return show

        score = 0.0

        if q_sig.issubset(t_sig):
            score += 1.0

        score += sig_overlap / max(len(q_sig), 1) * 0.5

        length_ratio = min(len(q), len(title)) / max(len(q), len(title))
        score += length_ratio * 0.5

        if q in title:
            score += 0.2

        if score > best_score:
            best_score, best = score, show

    return best if best_score > 0.3 else None


def extract_device_from_show_name(
    show_name: str,
    known_names: list[str],
) -> tuple[str, str]:
    """
    If Hassil greedily absorbed "on <device>" into show_name, split it out.

    Returns (cleaned_show_name, device_name).
    If no device is detected, returns (show_name, "").
    """
    if " on " not in show_name:
        return show_name, ""

    parts            = show_name.rsplit(" on ", 1)
    potential_device = parts[1].strip().lower()

    for name in known_names:
        n = name.lower()
        if n in potential_device or potential_device in n:
            return parts[0].strip(), parts[1].strip()

    return show_name, ""
