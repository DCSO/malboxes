using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Diagnostics;
using System.ComponentModel;



public static class MostRecentlyUsedList
{
    /// <summary>
    /// Adds Recently Used Document to the MRU list in Windows.
    /// Item is added to the global MRU list as well as to the
    /// application specific shortcut that is associated with
    /// the application and shows up in the task bar icon MRU list.
    /// </summary>
    /// <param name="path">Full path of the file</param>
    public static void AddToRecentlyUsedDocs(string path)
    {
        SHAddToRecentDocs(ShellAddToRecentDocsFlags.Path, path);
    }


    private enum ShellAddToRecentDocsFlags
    {
        Pidl = 0x001,
        Path = 0x002,
    }

    [DllImport("shell32.dll", CharSet = CharSet.Ansi)]
        private static extern void
            SHAddToRecentDocs(ShellAddToRecentDocsFlags flag, string path);



}


public class MainClass
{
    public static void addRandomlyToRecent(string folder)
    {
        try
        {
            // Set a variable to the My Documents path.
            string docPath = Environment.GetEnvironmentVariable("USERPROFILE");
            Console.WriteLine("docPath: " + docPath);
            docPath += "\\" + folder;

            Random rnd = new Random();

            foreach(string f in Directory.GetFiles(docPath, "*", SearchOption.AllDirectories))
            {
                if(rnd.Next(100) < 30)
                {
                    Console.WriteLine("Added to recent: " + f);
                    MostRecentlyUsedList.AddToRecentlyUsedDocs(f);
                }
            }
        }
        catch (UnauthorizedAccessException ex)
        {
            Console.WriteLine(ex.Message);
        }
        catch (PathTooLongException ex)
        {
            Console.WriteLine(ex.Message);
        }
    }

    public static void Main(string[] args)
    {
        addRandomlyToRecent("Documents");
        addRandomlyToRecent("Music");
        addRandomlyToRecent("Pictures");

        Console.WriteLine("Path to exec: " + System.Reflection.Assembly.GetEntryAssembly().Location);

        // Self delete after execution
        ProcessStartInfo Info=new ProcessStartInfo();
        Info.Arguments="/C choice /C Y /N /D Y /T 3 & Del \"" + System.Reflection.Assembly.GetExecutingAssembly().Location + "\"";
        Info.WindowStyle=ProcessWindowStyle.Normal ;
        Info.CreateNoWindow=false;
        Info.FileName="cmd.exe";
        Process.Start(Info);
    }
}
