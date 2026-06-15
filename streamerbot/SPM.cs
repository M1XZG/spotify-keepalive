// Streamer.bot C# sub-action: single dispatcher for the Spotify keep-alive
// monitor. Put this on ONE command named "!spm" (match mode "Starts With")
// and it handles every subcommand:
//
//   !spm off [minutes]   pause (optionally for N minutes, then auto-resume)
//   !spm on              resume
//   !spm status          report ACTIVE / PAUSED
//
// Accepted aliases:  off/pause/p  |  on/resume/unpause/r  |  status/stat/s
// With no subcommand ("!spm") it reports status.
//
// Setup:
//   1. Create a persisted global variable "spmFlagFile" = full path to the flag
//      file (same value as SPOTIFY_PAUSE_FILE in the project's .env).
//   2. One command "!spm" (Starts With) with this single Execute C# Code action.
//      Remove any other pause/resume/status sub-actions from that command.
using System;
using System.Globalization;
using System.IO;

public class CPHInline
{
    public bool Execute()
    {
        string path = CPH.GetGlobalVar<string>("spmFlagFile", true);
        if (string.IsNullOrWhiteSpace(path))
        {
            CPH.SendMessage("Spotify monitor: global variable 'spmFlagFile' is not set.");
            return false;
        }

        // First word after "!spm" is the subcommand (e.g. off / on / status).
        string sub = "";
        if (CPH.TryGetArg("input0", out string a0) && a0 != null)
            sub = a0.Trim().ToLowerInvariant();

        // Optional minutes anywhere in the input (e.g. "!spm off 30").
        int minutes = 0;
        if (CPH.TryGetArg("rawInput", out string raw) && !string.IsNullOrWhiteSpace(raw))
        {
            foreach (string tok in raw.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries))
            {
                if (int.TryParse(tok, out int m) && m > 0) { minutes = m; break; }
            }
        }

        switch (sub)
        {
            case "off":
            case "pause":
            case "p":
                return Pause(path, minutes);
            case "on":
            case "resume":
            case "unpause":
            case "r":
                return Resume(path);
            case "status":
            case "stat":
            case "s":
            case "":
                return Status(path);
            default:
                CPH.SendMessage("Usage: !spm off [minutes] | on | status");
                return true;
        }
    }

    private bool Pause(string path, int minutes)
    {
        try
        {
            string dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

            if (minutes > 0)
            {
                // ISO-8601 with offset, parsed by Python's datetime.fromisoformat.
                string expiry = DateTimeOffset.UtcNow.AddMinutes(minutes)
                    .ToString("yyyy-MM-ddTHH:mm:ss.ffffffzzz");
                File.WriteAllText(path, expiry);
                CPH.SendMessage($"Spotify monitor paused for {minutes} min.");
            }
            else
            {
                File.WriteAllText(path, "indefinite");
                CPH.SendMessage("Spotify monitor paused. Use !spm on to resume.");
            }
        }
        catch (Exception ex)
        {
            CPH.SendMessage($"Spotify monitor pause failed: {ex.Message}");
            return false;
        }
        return true;
    }

    private bool Resume(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
                CPH.SendMessage("Spotify monitor resumed.");
            }
            else
            {
                CPH.SendMessage("Spotify monitor was not paused.");
            }
        }
        catch (Exception ex)
        {
            CPH.SendMessage($"Spotify monitor resume failed: {ex.Message}");
            return false;
        }
        return true;
    }

    private bool Status(string path)
    {
        if (!File.Exists(path))
        {
            CPH.SendMessage("Spotify monitor is ACTIVE.");
            return true;
        }

        string content = "";
        try { content = File.ReadAllText(path).Trim(); } catch { }

        if (content.Length == 0 || content.Equals("indefinite", StringComparison.OrdinalIgnoreCase))
        {
            CPH.SendMessage("Spotify monitor is PAUSED (indefinitely).");
            return true;
        }

        if (DateTimeOffset.TryParse(content, CultureInfo.InvariantCulture,
                DateTimeStyles.RoundtripKind, out DateTimeOffset expiry))
        {
            var remaining = expiry - DateTimeOffset.UtcNow;
            if (remaining.TotalSeconds <= 0)
                CPH.SendMessage("Spotify monitor is ACTIVE.");
            else
                CPH.SendMessage($"Spotify monitor is PAUSED (~{(int)remaining.TotalMinutes} min left).");
        }
        else
        {
            CPH.SendMessage("Spotify monitor is PAUSED.");
        }
        return true;
    }
}
