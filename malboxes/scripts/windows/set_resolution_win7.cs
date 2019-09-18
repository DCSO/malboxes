using System;
using System.Runtime.InteropServices;
using System.Threading;
using System.Diagnostics;
using System.ComponentModel;
using System.Reflection;

namespace Resolution
{

    [StructLayout(LayoutKind.Sequential)]
    public struct DEVMODE1
    {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
            public string dmDeviceName;
        public short dmSpecVersion;
        public short dmDriverVersion;
        public short dmSize;
        public short dmDriverExtra;
        public int dmFields;

        public short dmOrientation;
        public short dmPaperSize;
        public short dmPaperLength;
        public short dmPaperWidth;

        public short dmScale;
        public short dmCopies;
        public short dmDefaultSource;
        public short dmPrintQuality;
        public short dmColor;
        public short dmDuplex;
        public short dmYResolution;
        public short dmTTOption;
        public short dmCollate;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
            public string dmFormName;
        public short dmLogPixels;
        public short dmBitsPerPel;
        public int dmPelsWidth;
        public int dmPelsHeight;

        public int dmDisplayFlags;
        public int dmDisplayFrequency;

        public int dmICMMethod;
        public int dmICMIntent;
        public int dmMediaType;
        public int dmDitherType;
        public int dmReserved1;
        public int dmReserved2;

        public int dmPanningWidth;
        public int dmPanningHeight;
    };


    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAY_DEVICE
    {
        public int cb;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string DeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string DeviceString;
        public int StateFlags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string DeviceID;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string DeviceKey;

         public override string ToString()
        {
           return String.Format(" cb: {0} \n DeviceName: {1} \n DeviceString: {2} \n StateFlags: {3} \n DeviceID: {4} \n DeviceKey: {5}", cb.ToString(), DeviceName, DeviceString, StateFlags.ToString(), DeviceID, DeviceKey);
        }
    }

    class User_32
    {
        [DllImport("user32.dll")]
            public static extern int EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE1 devMode);
        [DllImport("user32.dll")]
            public static extern int ChangeDisplaySettings(ref DEVMODE1 devMode, int flags);
        [DllImport("user32.dll")]
            public static extern bool EnumDisplayDevices(string deviceName, int modeNum, ref DISPLAY_DEVICE dsp, int flags);

        public const int ENUM_CURRENT_SETTINGS = -1;
        public const int CDS_UPDATEREGISTRY = 0x01;
        public const int CDS_TEST = 0x02;
        public const int DISP_CHANGE_SUCCESSFUL = 0;
        public const int DISP_CHANGE_RESTART = 1;
        public const int DISP_CHANGE_FAILED = -1;
    }



    public class PrmaryScreenResolution
    {
        static public string ChangeResolution(int width, int height)
        {

            DEVMODE1 dm = GetDevMode1();

            DISPLAY_DEVICE dsp = new DISPLAY_DEVICE();
            dsp.cb = Marshal.SizeOf(dsp);


            /* for(int i=0; true ; i++) */
            /* { */
            /*     if(!User_32.EnumDisplayDevices(null, i, ref dsp, 0)) */
            /*     { */
            /*         break; */
            /*     } */

            /* Console.WriteLine("DISPLAY_DEVICE: \n" + dsp.ToString()); */

            /*     if(dsp.DeviceString == "Standard VGA Graphics Adapter") */
            /*     { */
            /*         break; */
            /*     } */
            /* } */

            /* Console.WriteLine("Selected DISPLAY_DEVICE: \n" + dsp.ToString()); */

            if (0 != User_32.EnumDisplaySettings(null, User_32.ENUM_CURRENT_SETTINGS, ref dm))
            {

                dm.dmPelsWidth = width;
                dm.dmPelsHeight = height;

                int iRet = User_32.ChangeDisplaySettings(ref dm, User_32.CDS_TEST);

                if (iRet == User_32.DISP_CHANGE_FAILED)
                {
                    return "Unable To Process Your Request. Sorry For This Inconvenience.";
                }
                else
                {
                    iRet = User_32.ChangeDisplaySettings(ref dm, User_32.CDS_UPDATEREGISTRY);
                    switch (iRet)
                    {
                        case User_32.DISP_CHANGE_SUCCESSFUL:
                            {
                                return "Success";
                            }
                        case User_32.DISP_CHANGE_RESTART:
                            {
                                return "You Need To Reboot For The Change To Happen.\n If You Feel Any Problem After Rebooting Your Machine\nThen Try To Change Resolution In Safe Mode.";
                            }
                        default:
                            {
                                return "Failed To Change The Resolution";
                            }
                    }

                }


            }
            else
            {
                return "Failed To Change The Resolution.";
            }
        }

        private static DISPLAY_DEVICE GetDisplayDeviceStruct()
        {
            DISPLAY_DEVICE dsp = new DISPLAY_DEVICE();
            return dsp;
        }

        private static DEVMODE1 GetDevMode1()
        {
            DEVMODE1 dm = new DEVMODE1();
            dm.dmDeviceName = new String(new char[32]);
            dm.dmFormName = new String(new char[32]);
            dm.dmSize = (short)Marshal.SizeOf(dm);
            return dm;
        }
    }
}

public class MainClass
{
    public static void Main(string[] args)
    {
        Thread.Sleep(7000);
        int arg0 = Int32.Parse("{{ screen_width }}");
        int arg1 = Int32.Parse("{{ screen_height }}");
        string res = Resolution.PrmaryScreenResolution.ChangeResolution(arg0, arg1);
        Console.WriteLine("ChangeResolution returned: " + res + " Args[0]: " + arg0 + " Args[1]: " + arg1);


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
