# Kodi Voice Playback

A Home Assistant custom integration that adds a voice intent to play the next unwatched episode of any TV show in your Kodi library via Assist.

## What you can say

| Phrase | Example |
|---|---|
| Play the next episode of `<show>` | "Play the next episode of Breaking Bad" |
| Play the next episode of `<show>` on `<device>` | "Play the next episode of Gold Rush on lounge kodi" |
| Continue `<show>` | "Continue Drive to Survive" |
| Resume `<show>` on `<device>` | "Resume Lost on bedroom kodi" |
| Watch `<show>` | "Watch Our Zoo" |

## Requirements

- Kodi with the **HTTP API enabled**: Kodi → Settings → Services → Control → *Allow remote control via HTTP*
- Home Assistant **2023.8.0** or newer

## Installation via HACS

1. In HACS, go to **Integrations → Custom Repositories**
2. Add your repo URL with category **Integration**
3. Search for **Kodi Voice Playback** and install
4. Restart Home Assistant

## Manual installation

Copy the `custom_components/kodi_voice_playback` folder into your HA config's `custom_components/` directory and restart.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Kodi Voice Playback**
3. Enter your Kodi details:
   - **Voice name** — the word you say, e.g. `lounge` (then say "on lounge kodi")
   - **Host** — your Kodi IP address
   - **Port** — HTTP API port (default 8080)
   - **Username / Password** — leave blank if not configured in Kodi
4. Repeat for each Kodi device you want to control

## No extra YAML needed

Unlike the pyscript approach, this integration needs **no changes to `configuration.yaml`**, no `input_text` helpers, and no pyscript. Everything is handled by the integration itself.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "No Kodi instances configured" | Add the integration via Settings → Devices & Services |
| "Couldn't find `<show>`" | Run a library scan in Kodi first |
| Connection error during setup | Check the IP, port, and that HTTP API is enabled in Kodi |
| Intent not matched | Restart HA after installing; check the Assist debug panel |
