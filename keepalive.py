"""
Spotify keep-alive watchdog.

Keeps music continuously playing and pinned to one specific device.

How it works:
  - Polls your current playback state every POLL_SECONDS.
  - If nothing is playing (paused/stopped), it resumes playback.
  - If playback is happening on the WRONG device, it transfers it back to
    your TARGET device and keeps it playing there.
  - If there is no active context at all, it starts a fallback playlist/URI
    on the target device.

Requirements:
  - A Spotify *Premium* account (Web API playback control is Premium-only).
  - The target device must be online and visible to Spotify Connect.
  - A Spotify app registered at https://developer.spotify.com/dashboard
    with a redirect URI of http://127.0.0.1:8888/callback

Setup:
  pip install spotipy
  Set these environment variables (or fill them in .env / your shell):
    SPOTIPY_CLIENT_ID
    SPOTIPY_CLIENT_SECRET
    SPOTIPY_REDIRECT_URI   (e.g. http://127.0.0.1:8888/callback)

First run will open a browser to authorize. After that the token is cached.

Find your device name/id by running:  python keepalive.py --list-devices
"""

import argparse
import os
import subprocess
import sys
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load credentials/config from a local .env file (kept out of git) so secrets
# never have to be typed on the command line.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The exact name of the device you want music pinned to (as shown in Spotify
# Connect). Alternatively set TARGET_DEVICE_ID to a hard device id.
TARGET_DEVICE_NAME = os.environ.get("SPOTIFY_TARGET_DEVICE", "My Speaker")
TARGET_DEVICE_ID = os.environ.get("SPOTIFY_TARGET_DEVICE_ID")  # optional override

# What to start playing if absolutely nothing is queued/playing.
# Can be a playlist, album, or artist URI. Leave as-is to use a playlist.
FALLBACK_CONTEXT_URI = os.environ.get(
    "SPOTIFY_FALLBACK_URI",
    "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",  # "Today's Top Hits"
)

POLL_SECONDS = int(os.environ.get("SPOTIFY_POLL_SECONDS", "10"))

# How long to wait for the Spotify app to appear on Connect after launching it.
LAUNCH_WAIT_SECONDS = int(os.environ.get("SPOTIFY_LAUNCH_WAIT_SECONDS", "30"))

# Scopes needed to read and control playback.
SCOPE = "user-read-playback-state user-modify-playback-state"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client() -> spotipy.Spotify:
    auth = SpotifyOAuth(scope=SCOPE, open_browser=True, cache_path=".spotify_cache")
    return spotipy.Spotify(auth_manager=auth, requests_timeout=15)


def find_target_device(sp: spotipy.Spotify):
    """Return the target device dict if it is currently available, else None."""
    devices = sp.devices().get("devices", [])
    if TARGET_DEVICE_ID:
        for d in devices:
            if d["id"] == TARGET_DEVICE_ID:
                return d
        # Fall through to name matching: the Spotify desktop client can be
        # assigned a new device id each time it restarts, so a pinned id may
        # go stale after we relaunch the app.
    for d in devices:
        # Case-insensitive match so "HELIOS" matches a device named "Helios".
        if d["name"].casefold() == TARGET_DEVICE_NAME.casefold():
            return d
    return None


def launch_spotify() -> None:
    """Start the Spotify desktop app on Windows."""
    exe = os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe")
    try:
        if os.path.isfile(exe):
            subprocess.Popen([exe])
            print(f"[launch] Started Spotify ({exe}).", flush=True)
            return
    except Exception as e:  # noqa: BLE001 - fall back to the protocol handler
        print(f"[warn] Could not launch Spotify.exe directly: {e}", flush=True)
    # Fallback: the registered "spotify:" protocol handler (covers Store installs).
    try:
        os.startfile("spotify:")  # type: ignore[attr-defined]  # Windows-only
        print("[launch] Started Spotify via protocol handler.", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[error] Could not launch Spotify: {e}", flush=True)


def wait_for_target(sp: spotipy.Spotify, timeout: int):
    """Poll Spotify Connect until the target device appears, or until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        target = find_target_device(sp)
        if target is not None:
            return target
        time.sleep(2)
    return None


def check_device(sp: spotipy.Spotify) -> int:
    """Confirm the configured target device is currently visible.

    Returns 0 if the target was found, 1 otherwise.
    """
    target_label = TARGET_DEVICE_ID or TARGET_DEVICE_NAME
    target = find_target_device(sp)
    if target is None:
        print(f"[FAIL] Target device '{target_label}' is NOT visible to Spotify Connect.")
        print("       Make sure Spotify is open on that device, then try again.")
        print()
        print("Currently visible devices:")
        list_devices(sp)
        return 1

    print(f"[OK] Target device confirmed:")
    print(f"     NAME   : {target['name']}")
    print(f"     TYPE   : {target['type']}")
    print(f"     ID     : {target['id']}")
    print(f"     ACTIVE : {target['is_active']}")
    if not TARGET_DEVICE_ID and target['name'] != TARGET_DEVICE_NAME:
        print(
                f"     NOTE   : matched case-insensitively "
                f"(configured '{TARGET_DEVICE_NAME}', actual '{target['name']}')."
        )
    return 0


def list_devices(sp: spotipy.Spotify) -> None:
    devices = sp.devices().get("devices", [])
    if not devices:
        print("No devices visible. Open Spotify on the device you want to use.")
        return
    print(f"{'NAME':30} {'TYPE':12} {'ACTIVE':7} ID")
    print("-" * 90)
    for d in devices:
        print(f"{d['name']:30} {d['type']:12} {str(d['is_active']):7} {d['id']}")


def ensure_playing_on_target(sp: spotipy.Spotify) -> None:
    """Core watchdog logic: keep music playing on the target device."""
    target = find_target_device(sp)
    if target is None:
        print(
            f"[warn] Target device '{TARGET_DEVICE_ID or TARGET_DEVICE_NAME}' "
            "is not online/visible. Launching Spotify...",
            flush=True,
        )
        launch_spotify()
        target = wait_for_target(sp, LAUNCH_WAIT_SECONDS)
        if target is None:
            print(
                "[warn] Spotify did not appear on Connect in time. "
                "Will retry next cycle.",
                flush=True,
            )
            return
        print(f"[ok] Spotify is now available on '{target['name']}'.", flush=True)
        _start_fresh(sp, target["id"])
        return

    target_id = target["id"]
    playback = sp.current_playback()

    # Case 1: nothing playing at all -> start playback on target.
    if playback is None or playback.get("device") is None:
        _start_fresh(sp, target_id)
        return

    current_device_id = playback["device"]["id"]
    is_playing = playback.get("is_playing", False)

    # Case 2: playing on the WRONG device -> transfer to target (keep playing).
    if current_device_id != target_id:
        print(f"[move] Transferring playback to '{target['name']}'", flush=True)
        sp.transfer_playback(device_id=target_id, force_play=True)
        return

    # Case 3: on the right device but paused/stopped -> resume.
    if not is_playing:
        print("[resume] Playback was paused/stopped. Resuming.", flush=True)
        try:
            sp.start_playback(device_id=target_id)
        except spotipy.SpotifyException:
            # No existing context to resume; start the fallback.
            _start_fresh(sp, target_id)
        return

    # Case 4: everything is fine.


def _start_fresh(sp: spotipy.Spotify, target_id: str) -> None:
    print(f"[start] Starting fallback playback on target device.", flush=True)
    try:
        if FALLBACK_CONTEXT_URI.startswith("spotify:track:"):
            sp.start_playback(device_id=target_id, uris=[FALLBACK_CONTEXT_URI])
        else:
            sp.start_playback(device_id=target_id, context_uri=FALLBACK_CONTEXT_URI)
        # Make sure repeat is on so a playlist never simply ends.
        sp.repeat("context", device_id=target_id)
    except spotipy.SpotifyException as e:
        print(f"[error] Could not start playback: {e}", flush=True)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Keep Spotify always playing on one device.")
    parser.add_argument("--list-devices", action="store_true", help="List visible devices and exit.")
    parser.add_argument(
        "--check-device",
        action="store_true",
        help="Confirm the configured target device is visible, then exit.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check-and-fix pass, then exit (for Task Scheduler).",
    )
    args = parser.parse_args()

    sp = get_client()

    if args.list_devices:
        list_devices(sp)
        return 0

    if args.check_device:
        return check_device(sp)

    if args.once:
        try:
            ensure_playing_on_target(sp)
        except spotipy.SpotifyException as e:
            print(f"[api-error] {e}", flush=True)
        except Exception as e:
            print(f"[error] {e}", flush=True)
        return 0

    print(
        f"Watchdog started. Target='{TARGET_DEVICE_ID or TARGET_DEVICE_NAME}', "
        f"poll every {POLL_SECONDS}s. Press Ctrl+C to stop.",
        flush=True,
    )
    while True:
        try:
            ensure_playing_on_target(sp)
        except spotipy.SpotifyException as e:
            print(f"[api-error] {e}", flush=True)
        except Exception as e:  # keep the watchdog alive through transient errors
            print(f"[error] {e}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
