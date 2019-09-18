# Malboxes Fork

Builds malware analysis Windows virtual machines so that you don't have to.

## Requirements

* Python 3.6+
* packer (tested with v1.3.4)
* VirtualBox (no extension pack needed)
* sshpass (optional)    --> To be able to ssh into vm through malboxes
* pwsh (optional) --> Needed to syntax check csharp scripts locall  
Python dependencies:
   * appdirs
   * Jinja2>=2.9
   * jsmin
   * requests
   * tqdm

If you are using a python version below 3.6 you have to execute:
`$ pip3 install python2-secrets`



# Installation

## Linux/Unix

* Install git and packer using your distribution's packaging tool
  (packer is sometimes called packer-io)
* `pip install` malboxes:
    ```
    pip3 install git+ssh://git@github.com:DCSO/malboxes.git
    ```

## Windows
* Not tested on Windows so there are probably bugs.
But in general it should work on Windows too

## Currently working deployments are
* win7_64_analyst

## Usage

To execute malboxes use: `python3 -m malboxes`

```
usage: malboxes [-h] [-V] [-d] [-p PROFILE] [-s SSH] [--ip IP] [-c CONFIG]
                {list,build} ...

Windows image generator

positional arguments:
  {list,build}
    list                Lists available templates.
    build               Builds a Windows virtualmachine based on a given
                        template.

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -d, --debug           Debug mode. Leaves built VMs running on failure!
  -p PROFILE, --profile PROFILE
                        Define which profile to use
  -s SSH, --ssh SSH     SSH into VM through credentials in the description
  --ip IP               Define the ip to SSH into VM
  -c CONFIG, --config CONFIG
                        Override the configuration file with the one
                        specified.


supported templates:

win7_64_analyst
```

Building a vm with debug output:
`
$ python3 -m malboxes -d win7_64_analyst_default_0
`

SSH into build vm:
`
$ python3 -m malboxes -s win7_64_analyst_default_0 --ip 192.168.56.5
`


## Defaults
Every Windows VM starts with 4GB of memory and 128M of video memory
and 120G of storage.

If you run multiple Windows VMs make sure that you have enough video memory and
RAM.

The defaults can be looked up in: [malboxes/malboxes.py](malboxes/malboxes.py) in the method
`def default_settings(config):`


## Configuration

Malboxes' configuration is located in a directory that follows usual operating
system conventions:

* Linux/Unix: `~/.config/malboxes/`
* Mac OS X: `~/Library/Application Support/malboxes/`
* Win 7+: `C:\Users\<username>\AppData\Local\malboxes\malboxes\`

The file is named `config.js` and is copied from an example file on first run.   
[malboxes/config-example.js](malboxes/config-example.js) is documented.   
[malboxes/profile-example.js](malboxes/profile-example.js) is documented.  

Profiles are located in `<somepath>/malboxes/profiles` if no profile is defined
it tries to load the `default.js` profile.


## Generate VMs
The vm base folder is the same as the VirtualBox default machine folder, which can be queried with
```
$ VBoxManage list systemproperties | grep "Default machine folder" | awk '{ print $4 }'
```
The generate vm name can be set in the config or be overriden in the profile, if no vm_name has been set
malboxes generates a vm name like this "<template_name><profile_name><counter>"

## Notes
This script uses chocolatey to install software on a Windows vm. If you deploy a lot of Windows instances it
is a good idea to set up a chocolatey proxy like [Nexus](https://www.sonatype.com/download-oss-sonatype) to prevent hitting
API limits.


## Logs
With the -d or --debug option the logs are saved to the vm folder where the vm image resides.
So for example under `~/VirtualBox\ VMs/win7_64_analyst_0`:
* packerlog.txt --> The verbose Packer output with color codes
* packer_var_file.json --> A minified json file with all configuration variables
* win7_64_analyst.json --> The packer template generated from malboxes
* Other files --> Temporary files that get uploaded into the guest

## Minimum specs for the build machine

* At least 8 GB of RAM and 3 cpu cores
* VT-X extensions strongly recommended

## Differences to original [malboxes](https://github.com/GoSecure/malboxes)
* Parallel builds. It is now possible to build multiple vms in parallel
* Setting a static ip and dns server in the guest
* Username, Password & Computername get written as json to the description of the vm
* No guest additions needed anymore.
* Better defined behaviour as to when a profile script executes and in what order
* Convenience function to ssh into vm from malboxes
* Added following profile keywords:
    * overwrite                   --> overide the main config in the profile
    * onstartup_powershell_inline --> The poweshell script will be installed as a task scheduler service as a one liner (base64).
    * onstartup_powershell_file   --> The poweshell script will be uploaded & installed as a task scheduler service.
    * onstartup_csharp            --> Csharp source file gets compiled on guest and then registered as task scheduler service.
    * upload_onstartup            --> Uploads a file to the autostart folder of the current user (Admininistrator)
    * upload_execute              --> Uploads an executable and executes it on the host. Removes it afterwards
    * upload_compile_execute      -->  Csharp source file gets compiled on guest and then executed, afterwards removed.
* Added following config keywords:
    * win7_64_iso_name, win7_64_iso_download, win7_64_user_agent, win7_64_checksum
    * username, password, computername
    * disk_size, vm_name, cpus, memory, vram
    * windows_testsigning                       --> Enable Windows testsigning
    * windows_firewall                          --> Eable / Disable Windows firewall
    * choco_source                              --> Sets the choco source server
    * flare_source                              --> Set flare packages source server
    * screen_width, screen_height               --> Set screen width / screen height
    * openssh_server                            --> Setup an openssh server
    * winrm                                     --> Enable / Disable winrm
    * guestadditions                            --> Enable / Disable guest additions
    * generate_random_files                     --> Generates random files for Admininistrator user
    * hide_vm_artifacts                         --> Removes virtualbox artifacts
    * cleanup                                   --> Clears temp dir and uninstall chocolatey
    * guest_ip, gateway_ip, netmask             --> Sets the static ip on the guest
    * dnsserver_ip                              --> Sets a custom dns server


## License

Code is licensed under the GPLv3+, see `LICENSE` for details. Documentation
and presentation material is licensed under the Creative Commons
Attribution-ShareAlike 4.0, see `docs/LICENSE` for details.


## Forked from
https://github.com/GoSecure/malboxes
