// Streamer.bot C# sub-action: RESUME the Spotify keep-alive monitor (!spm on).
//
// Setup:
//   1. Requires the persisted global variable "spmFlagFile" (see SPM_Pause.cs).
//   2. Add this code to an "Execute C# Code" sub-action on your !spm on command.
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
}
