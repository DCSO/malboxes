{
    // Define the base directory of the iso files
    "iso_dir": "~/ISO",

    "win7_64_iso_name": "7600.16385.090713-1255_x64fre_enterprise_en-us_EVAL_Eval_Enterprise-GRMCENXEVAL_EN_DVD.iso",
    "win7_64_iso_download": "http://care.dlservice.microsoft.com/dl/download/evalx/win7/x64/EN/7600.16385.090713-1255_x64fre_enterprise_en-us_EVAL_Eval_Enterprise-GRMCENXEVAL_EN_DVD.iso",
    "win7_64_checksum": "15ddabafa72071a06d5213b486a02d5b55cb7070", // The sha1 checksum for the iso
    //"win7_64_user_agent": "",

    // Trial or registered version?
    // If using a registered product update the product_key and set trial to 'false'.
    // See https://github.com/GoSecure/malboxes/blob/master/docs/windows-licenses.adoc for more information.
    "trial": "true",
    //"trial": "false",
    //"product_key": "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX",

    // VM settings
    //"username": "Mani", // If not defined generated randomly
    //"password": "ManiPassword", // If not defined generated randomly
    //"computername": "Mani", // If not defined generated randomly
    //"disk_size": "114441", // in Megabytes (default 120 GB to avoid VM detection)
    "input_locale": "de-DE",


    // "windows_defender": "false",
    "windows_updates": "false",
    "windows_firewall": "true",
    // "windows_testsigning": "true",
    //"choco_packages": "firefox",
    "choco_source": "https://chocolatey.org/api/v2/",

    "enable_flare_source": "false",
    "flare_source": "https://www.myget.org/F/flare/api/v2",

    // // Which Hypervisor for privisoning and deployment? (Options are: "virtualbox" and "vsphere") Default is "virtualbox"
    "hypervisor": "virtualbox",
    "guestadditions": "false", // Toggle guest additions (only virtualbox)
    "screen_width": "1600",
    "screen_height":"1200",
    "openssh_server": "true",
    "winrm": "false", // Set to true if you want remote winrm over http
    "generate_random_files": "true", // Creates files randomly in the vm

    // Currently only works for virtualbox. Hides artifacts to detect VirtualBox
    // It creates a randomly named scheduled task with inline powershell that
    // deletes VirtualBox Registry keys
    "hide_vm_artifacts": "true",

    // Deletes choco and all its folders & clears tmp folders.
    // Programs without an installer residing in the choco folder will be deleted
    "cleanup": "false",

    "set_static_ip": "false", // The options below are only valid if this is set to true
    "guest_ip": "192.168.77.6",
    "gateway_ip": "192.168.77.1",
    "netmask": "255.255.255.0",
    "dnsserver_ip": "192.168.77.1", // This is optional and doesn't have to be set

    // TESTING, not working flawlessly!
    // Installs flare vm: https://github.com/fireeye/flare-vm
    "flare_vm": "false",

    // // Keeps the VM registered after build
    // "keep_registered": "true",
    // "skip_export": "true", // Packer will not export the VM
    //"vm_name": "Win7_64_testname",
    // "cpus": "2", // Number of cpus to use ( Use at least 2 to avoid VM detection)
    // "vram": "128", // Mb of video RAM to be used
    // "memory": "4096", // Mb of RAM to be used

	// Setting the IDA Path will copy the IDA remote debugging tools into the guest
    //"ida_path": "/path/to/your/ida",

    // You can also use the --profile (-p) option to define
    // a profile on the fly. If defined as argument it overrides the profile defined here.
    "profile": "default",

    // Setting Tools Path will copy all the files under the given path into the guest to
    // C:\Tools. These files will be uploaded before executing the scripts defined in the profile.
    // Useful to copy proprietary or unpackaged tools.
    // Note: packer's file provisonning is really slow, avoid having more than
    // 100 megabytes in there.
    //"tools_path": "~/guest-bins",

    "_comment": "last line must finish without a comma for file to be valid json"
}
