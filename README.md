# Kodi Voice Playback

A Home Assistant custom integration that adds voice commands to play the next unwatched TV episode or any movie in your Kodi library via Assist.

## What you can say

| Phrase | Example |
|---|---|
| Play the next episode of `<show>` | "Play the next episode of Breaking Bad" |
| Play the next episode of `<show>` on `<device>` | "Play the next episode of Gold Rush on lounge kodi" |
| Continue `<show>` | "Continue Drive to Survive" |
| Resume `<show>` on `<device>` | "Resume Lost on bedroom kodi" |
| Watch `<show>` | "Watch Our Zoo" |
| Play the movie `<title>` | "Play the movie Minions" |
| Play the movie `<title>` on `<device>` | "Play the movie Interstellar on lounge kodi" |
| Watch the movie `<title>` | "Watch the movie Minions" |
| Resume the movie `<title>` | "Resume the movie Minions on lounge" |

The word **"movie"** is required when asking for a film, so that "play Minions" doesn't ambiguously match TV shows too.

---

## Requirements

- Kodi with the **HTTP API enabled**: Kodi → Settings → Services → Control → *Allow remote control via HTTP*
- Home Assistant **2023.8.0** or newer

---

## How it works

The integration uses Home Assistant's built-in Hassil sentence engine to match your voice commands locally — no LLM required. When a sentence matches, a Python intent handler talks directly to Kodi's JSON-RPC API to find and play the right content.

**Important:** Hassil only loads sentence files at HA startup. This means after installation, **one full HA restart is required** before voice commands will work. This is a Home Assistant limitation — there is no supported API for integrations to inject sentences at runtime.

---

## Installation

### Step 1 — Copy the integration files

Copy the `custom_components/kodi_voice_playback` folder into your HA config's `custom_components/` directory:

```
/config/custom_components/kodi_voice_playback/
```

### Step 2 — Copy the sentences file (important!)

This is the step most people miss. Copy the sentences file **before your first restart** so HA loads it on startup:

```
From zip:  custom_sentences/en/kodi_voice_playback.yaml
To:        /config/custom_sentences/en/kodi_voice_playback.yaml
```

Create the `/config/custom_sentences/en/` folder if it doesn't exist.

> If you skip this step, the integration will copy the file automatically on first setup, but you will need **a second HA restart** for the sentences to take effect.

### Step 3 — Restart Home Assistant

Do a full HA restart (not just a reload). This is required for Hassil to pick up the new sentences file.

### Step 4 — Add the integration

Go to **Settings → Devices & Services → Add Integration** and search for **Kodi Voice Playback**.

Enter your Kodi details:

| Field | Description |
|---|---|
| **Voice name** | The word you say — e.g. `lounge` lets you say "on lounge kodi" |
| **Host** | Your Kodi device's IP address |
| **Port** | HTTP API port (default: 8080) |
| **Username** | Leave blank if not configured in Kodi |
| **Password** | Leave blank if not configured in Kodi |

Repeat for each Kodi device you want to control.

### Step 5 — Verify

Go to **Developer Tools → Assist** and use the sentence tester. Type:

```
play the next episode of drive to survive on lounge
```

It should return a matched intent. If it returns `null`, the sentences file has not been loaded — check that the file exists at `/config/custom_sentences/en/kodi_voice_playback.yaml` and do another full restart.

### HACS installation

1. In HACS, go to **Integrations → Custom Repositories**
2. Add your repo URL with category **Integration**
3. Search for **Kodi Voice Playback** and install
4. Follow steps 2–4 above (the sentences file is included in the HACS download)

---

## Multiple Kodi devices

Add the integration multiple times — once per Kodi device. Give each a distinct voice name:

- `lounge` → "play next episode of Seinfeld **on lounge kodi**"
- `bedroom` → "play next episode of Seinfeld **on bedroom kodi**"

If you only have one Kodi instance, you can omit the device name entirely:

- "play next episode of Seinfeld"

---

## Episode selection

1. Fetches all unplayed episodes of the matched show, sorted by season and episode number
2. If any episode has a **resume position** (partially watched), that episode plays first and Kodi resumes from where you left off
3. Otherwise the **lowest unplayed episode** plays (S01E01, S01E02, …)
4. If every episode has been watched, you'll hear a message saying so

---

## Show and movie title matching

You don't need to say the exact title. The integration uses a layered fuzzy-matching strategy:

1. Exact match
2. Query is a substring of the title ("wire" → *The Wire*)
3. All query words appear in the title
4. Word-overlap score with stop words filtered out (so "on", "the", "of" don't influence the match)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sentence parser returns `null` | Check `/config/custom_sentences/en/kodi_voice_playback.yaml` exists, then do a full HA restart |
| "No Kodi instances configured" | Add the integration via Settings → Devices & Services |
| "Couldn't find `<show>`" | Run a library scan in Kodi first |
| Wrong show matched | Try saying more of the title; the fuzzy matcher may be picking a similarly-named show |
| Connection error during setup | Check the IP, port, and that HTTP API is enabled in Kodi |
| Command goes to Ollama instead of matching locally | The sentences file isn't loaded — see sentence parser check above |
| Setup succeeds but sentences still don't work after restart | Confirm the file is at the exact path `/config/custom_sentences/en/kodi_voice_playback.yaml` (not inside `custom_components/`) |

Check **Settings → System → Logs** and filter for `kodi_voice_playback` for detailed logs.

---

## No extra YAML needed

Unlike a pyscript-based approach, this integration needs **no changes to `configuration.yaml`**, no `input_text` helpers, no `intent_script` blocks, and no pyscript. Everything is handled by the integration itself — the only manual step is copying the sentences file before the first restart.

---

## License

MIT — see [LICENSE](LICENSE)
