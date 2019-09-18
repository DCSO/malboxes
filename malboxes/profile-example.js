{
    "overwrite": {
        // "username": "Mombo"
    },

    // NOTE: Execution directory of all here defined things is the home folder of the admin user!

    // Changes made here will be called before the scripts in the "script" setting
    //"extra_choco_packages": "procmon", // Space separated list of additional packages
    "directory": [
        // {"modtype": "add", "dirpath": "C:\\mlbxs\\"}
    ],

    "shortcut": [
        // Create shortcuts to Desktop
        {"dest": "Autostart.lnk", "target": "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"}
    ],

    "onstartup_powershell_inline": [
        //  {"src": "~/test1.ps1" }
    ],

    "onstartup_powershell_file": [
        // {"src": "~/test1.ps1", "dest": "$env:HOMEDRIVE\\test.ps1" }
    ],

    // Uploads the csharp file compiles it and registers it to task scheduler on bootup
    "onstartup_csharp": [
        //   {"src": "~/test.cs", "args": "" }
    ],


    // This one is special it uploads the file to the startup directory of the main user
    // this has to be a binary or a batch file. It gets executed with the context of the
    // window manager and current user
    "upload_onstartup": [

    ],

    // Uploads the file and executes it with defined args. Removes it afterwards.
    // It has to be a binary with no dependencies or a .bat file. Gets executed before anything defined here.
    // Do NOT use blocking scripts or scripts that need user input. This will halt the build process.
    "upload_execute": [
        // {"src": "~/pafish.exe", "args": "" }
    ],

    // Uploads the csharp file compiles it on the host and executes it
    "upload_compile_execute": [
        //  {"src": "~/test.cs", "args": "" }
    ]
}
