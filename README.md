# Spotify Keep-Alive Watchdog

Keeps Spotify continuously playing music and pinned to **one specific device**.
If playback pauses, it resumes. If it jumps to another device, it gets pulled
back to your chosen device. If nothing is queued, a fallback playlist starts on
repeat so the music never simply ends.

## Requirements

- **Spotify Premium** (the Web API only allows playback control on Premium).
- The target device must be **online and visible** to Spotify Connect
  (app open / speaker powered on).
- Python 3.8+.

## 1. Register a Spotify app

1. Go to <https://developer.spotify.com/dashboard> and create an app.
2. In the app settings, add a Redirect URI: `http://127.0.0.1:8888/callback`
3. Copy the **Client ID** and **Client Secret**.

## 2. Install

```pwsh
cd spotify_keepalive
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Configure (PowerShell)

```pwsh
$env:SPOTIPY_CLIENT_ID     = "your_client_id"
$env:SPOTIPY_CLIENT_SECRET = "your_client_secret"
$env:SPOTIPY_REDIRECT_URI  = "http://127.0.0.1:8888/callback"

# Set the device you want music pinned to (exact name from Spotify Connect):
$env:SPOTIFY_TARGET_DEVICE = "Living Room"

# Optional overrides:
# $env:SPOTIFY_TARGET_DEVICE_ID = "abc123..."         # pin by id instead of name
# $env:SPOTIFY_FALLBACK_URI     = "spotify:playlist:..."  # what to play if idle
# $env:SPOTIFY_POLL_SECONDS     = "10"
```

## 4. Find your device name/id

Start playing something on the device first, then:

```pwsh
python keepalive.py --list-devices
```

Use the exact `NAME` (or the `ID`) for the target settings above.

## 5. Run

```pwsh
python keepalive.py
```

First run opens a browser for one-time authorization. After that the token is
cached in `.spotify_cache`. Leave the script running; press `Ctrl+C` to stop.

## Notes & limitations

- Spotify cannot transfer to a device it can't see. If the speaker/app is fully
  off, the watchdog waits until it reappears.
- Some devices (e.g. certain TVs) drop off Connect when idle; keep the app
  alive on that device for best results.
- This uses your own account and Spotify's official API — no terms-of-service
  workarounds. It just automates the normal play/transfer buttons.
- To run it unattended, use Windows Task Scheduler (run at logon) or a
  `pythonw keepalive.py` background process.
```
