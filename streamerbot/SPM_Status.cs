// Streamer.bot C# sub-action: report the Spotify keep-alive monitor STATUS (!spm status).
//
// Mirrors the Python is_paused() logic:
//   - no file            -> ACTIVE
//   - empty/"indefinite" -> PAUSED (indefinitely)
//   - future timestamp   -> PAUSED (with minutes remaining)
//   - past timestamp     -> ACTIVE (Python deletes it on its next run)
//
// Setup:
//   1. Requires the persisted global variable "spmFlagFile" (see SPM_Pause.cs).
//   2. Add this code to an "Execute C# Code" sub-action on your !spm status command.
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
