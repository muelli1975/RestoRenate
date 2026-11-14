using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;

[assembly: System.Reflection.AssemblyTitle("RestoRenate")]
[assembly: System.Reflection.AssemblyProduct("RestoRenate")]
[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.0.0.0")]

internal static class RestoRenateLauncher
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBox(IntPtr window, string text, string caption, uint type);

    private static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string runtime = Path.Combine(root, "runtime", "python");
        string python = Path.Combine(runtime, "pythonw.exe");
        string bootstrap = Path.Combine(root, "bootstrap.py");
        if (!File.Exists(python) || !File.Exists(bootstrap))
        {
            MessageBox(IntPtr.Zero, "Bitte die ZIP vollständig entpacken.\nExtract the entire ZIP.", "RestoRenate", 0x10);
            return 1;
        }

        try
        {
            var start = new ProcessStartInfo(python, "-I -X utf8 \"" + bootstrap + "\" --gui");
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.EnvironmentVariables["TCL_LIBRARY"] = Path.Combine(runtime, "tcl", "tcl8.6");
            start.EnvironmentVariables["TK_LIBRARY"] = Path.Combine(runtime, "tcl", "tk8.6");
            using (Process.Start(start)) { }
            return 0;
        }
        catch (Exception exception)
        {
            MessageBox(IntPtr.Zero, exception.Message, "RestoRenate", 0x10);
            return 1;
        }
    }
}
