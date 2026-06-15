# Streamer.bot Control (`!spm` commands)

Pause and resume the keep-alive monitor from chat — handy when you need Spotify
to play on another device (e.g. your phone in the car) without the watchdog
yanking playback back to the target PC.

It works through a single **pause flag file**. While that file exists the
watchdog does nothing. Streamer.bot just creates it (pause) or deletes it
(resume); the Python side honours it on every 2-minute cycle.

| Chat command | Action | Effect |
| --- | --- | --- |
| `!spm off` | create flag (`indefinite`) | Pause until you resume |
| `!spm off 30` | create flag with a 30-min expiry | Pause, then auto-resume after 30 **minutes** |
| `!spm on` | delete flag | Resume immediately |
| `!spm status` | read flag | Report ACTIVE / PAUSED (+ minutes left) |

> **The pause number is in minutes**, e.g. `!spm off 30` pauses for 30 minutes.
> An expired pause is cleared by the watchdog on its next 2-minute cycle, so it
> may resume up to ~2 minutes after the deadline. Pauses shorter than the
> watchdog interval aren't meaningful.

## Quick import

The whole setup (command + action) can be imported in one step. In Streamer.bot
go to **Import**, paste the string from
[streamerbot/spotify-monitor-import.sb](streamerbot/spotify-monitor-import.sb),
and import. Then just set the `spmFlagFile` global variable (step 2 below) to
your flag path. If you import, you can skip step 3.

## 1. Point Python and Streamer.bot at the same file

In the project's `.env`, set the flag path:

```
SPOTIFY_PAUSE_FILE=C:\Users\you\GitHub\spotify-keepalive\spm_pause.flag
```

If you omit it, the default is `spm_pause.flag` next to `keepalive.py`.

## 2. Create the Streamer.bot global variable

Create a **persisted** global variable named `spmFlagFile` whose value is the
exact same path as `SPOTIFY_PAUSE_FILE` above.

- Via UI: **Variables → Global Variables → Add** (set Persisted = true), or
- Via an action: add a one-off **Execute C# Code** sub-action containing
  `CPH.SetGlobalVar("spmFlagFile", @"C:\Users\you\GitHub\spotify-keepalive\spm_pause.flag", true);`
  and run it once.

## 3. Add the command

One command handles every subcommand. Create a command with trigger `!spm` and
**match mode "Starts With"**, then add a single **Execute C# Code** sub-action
containing [streamerbot/SPM.cs](streamerbot/SPM.cs). It routes:

| You type | Branch |
| --- | --- |
| `!spm off` / `!spm pause` / `!spm p` | pause (add a number for minutes, e.g. `!spm off 30`) |
| `!spm on` / `!spm resume` / `!spm r` | resume |
| `!spm status` / `!spm s` / `!spm` | status |

Restrict the command to **broadcaster/mods** so viewers can't toggle your music.

## How the flag is interpreted

Both sides agree on the same rules:

| Flag file state | Meaning |
| --- | --- |
| does not exist | ACTIVE (monitor enforcing) |
| empty or `indefinite` | PAUSED until resumed |
| ISO-8601 timestamp in the future | PAUSED, auto-resumes at that time |
| ISO-8601 timestamp in the past | ACTIVE (Python deletes it on next run) |

Timed pauses set in chat use an ISO-8601 timestamp that Python's
`datetime.fromisoformat` reads, and the `SPM.cs` status branch parses Python's
format too — so chat and the `--status` CLI always agree regardless of which
side created the flag.

## CLI equivalents

The same controls exist on the command line for testing:

```pwsh
python keepalive.py --pause       # pause indefinitely
python keepalive.py --pause 30    # pause 30 minutes
python keepalive.py --resume      # resume
python keepalive.py --status      # show ACTIVE / PAUSED
```
