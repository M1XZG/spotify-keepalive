// Streamer.bot C# sub-action: PAUSE the Spotify keep-alive monitor (!spm off).
//
// Setup:
//   1. Create a persisted global variable named "spmFlagFile" holding the full
//      path to the flag file, e.g. C:\Users\rmcke\GitHub\spotify-keepalive\spm_pause.flag
//      (must match SPOTIFY_PAUSE_FILE in the project's .env).
//   2. Add this code to an "Execute C# Code" sub-action on your !spm off command.
//
// Optional: "!spm off 30" pauses for 30 minutes; the Python watchdog then
// auto-resumes when the timestamp expires. With no number it pauses until !spm on.
using System;
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

        // Parse an optional minutes value from the command input (e.g. "!spm off 30").
        int minutes = 0;
        if (CPH.TryGetArg("rawInput", out string raw) && !string.IsNullOrWhiteSpace(raw))
        {
            foreach (string token in raw.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries))
            {
                if (int.TryParse(token, out int m) && m > 0) { minutes = m; break; }
            }
        }

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
}
