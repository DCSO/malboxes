#!/usr/bin/env python

# Malboxes - Vagrant box builder and config generator for malware analysis
# https://github.com/gosecure/malboxes
#
# Olivier Bilodeau <obilodeau@gosecure.ca>
# Hugo Genesse <hugo.genesse@polymtl.ca>
# Copyright (C) 2016, 2017 GoSecure Inc.
# Copyright (C) 2016 Hugo Genesse
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
import argparse
import glob
import json
import os
from pkg_resources import resource_filename, resource_stream
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import requests
from tqdm import tqdm
import time
import random

try:
    import secrets
except ImportError:
    print("""
    Could not find module 'secrets'. You are probably
    using a python version below 3.6. Execute
    $ pip3 install python2-secrets
    for compatibility.
    """)

import string
import datetime
import base64

from appdirs import AppDirs
from jinja2 import Environment, FileSystemLoader
from jsmin import jsmin

from malboxes._version import __version__


DIRS = AppDirs("malboxes")
VM_DIR_BASE = ""
CURRENT_VM_DIR = ""
DEBUG = False
PACKER_LOG_PATH = "packerlog.txt"
tempfiles = []


def initialize():
    # create appdata directories if they don't exist
    if not os.path.exists(DIRS.user_config_dir):
        os.makedirs(DIRS.user_config_dir)

    profile_dir = os.path.join(DIRS.user_config_dir, "profiles")

    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)

    global VM_DIR_BASE
    VM_DIR_BASE = get_default_machine_folder()

    if not os.path.exists(VM_DIR_BASE):
        os.makedirs(VM_DIR_BASE)

    iso_dir = os.path.join(DIRS.user_cache_dir, "iso")
    if not os.path.exists(iso_dir):
        os.makedirs(iso_dir)

    return init_parser()


def init_parser():
    parser = argparse.ArgumentParser(
        description="Windows image generator"
    )
    parser.add_argument(
        "-V", "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug mode. Leaves built VMs running on failure!",
    )
    parser.add_argument(
        "-p",
        "--profile",
        type=argparse.FileType("r"),
        help="Define which profile to use",
    )
    parser.add_argument(
        "-s",
        "--ssh",
        action="store",
        help="SSH into VM through credentials in the vm description",
    )
    parser.add_argument(
        "--ip",
        action="store",
        help="Define the ip to SSH into VM",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=argparse.FileType("r"),
        help="Override the configuration file with the one specified.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # list command
    parser_list = subparsers.add_parser("list", help="Lists available templates.")
    parser_list.set_defaults(func=list_templates)

    # build command
    parser_build = subparsers.add_parser(
        "build", help="Builds a Windows virtualmachine based on a given template."
    )
    parser_build.add_argument(
        "template",
        help="Name of the template to build. "
        "Use list command to view "
        "available templates.",
    )
    parser_build.add_argument(
        "--force",
        action="store_true",
        help="Force the build to happen. Overwrites "
        "pre-existing builds or vagrant boxes.",
    )
    parser_build.set_defaults(func=build)



    # no command
    parser.set_defaults(func=default)

    args = parser.parse_args()
    return parser, args


def ssh_into_vm(vm_name, ip):
    vms = run_background(["VBoxManage", "list", "vms"])

    found = False

    for line in vms.split("\n"):
        if line != "":
            row = line.split(" ")[0].strip('"')

            if vm_name == row:
                found = True
                break

    if not found:
        print("Defined vm name does not exist: {}".format(vm_name))
        sys.exit(1)

    vm_info = run_background(["VBoxManage", "showvminfo", vm_name])

    vm_credentials = ""
    r = re.compile("{\"username\": ")

    try:
        for line in vm_info.split("\n"):
            temp = r.search(line)

            if temp is not None:
                vm_credentials = line[temp.span(0)[0]:]
    except AttributeError as ex:
        print(
            "Parsing command 'VBoxManage showvminfo {}' failed. Did the command output change?".format(vm_name)
        )
        print("Command output: {}".format(vm_info))
        raise ex

        print("VM credentials: {}".format(vm_credentials))

    vm_credentials = json.loads(vm_credentials)
    print(vm_credentials)

    if ip is None:
        if "static_ip" in vm_credentials.keys():
            ip = vm_credentials["static_ip"]
        else:
            print("Ip has to be specified through --ip")
            sys.exit(2)

    username = vm_credentials["username"]
    password = vm_credentials["password"]

    print("username: {} password: {}".format(username, password))

    if shutil.which("sshpass") is None:
        print("command 'sshpass' not found in PATH.")
        sys.exit(1)

    command = ["sshpass -p {} ssh {}@{} -o StrictHostKeyChecking=no".format(password, username, ip)]
    subprocess.run(command, stdout=sys.stdout, stdin=sys.stdin, shell=True)


def prepare_autounattend(config):
    """
    Prepares an Autounattend.xml file according to configuration and writes it
    into a temporary location where packer later expects it.

    Uses jinja2 template syntax to generate the resulting XML file.
    """
    os_type = _get_os_type(config)

    filepath = resource_filename(__name__, "installconfig/")
    env = Environment(loader=FileSystemLoader(filepath))
    template = env.get_template("{}/Autounattend.xml".format(os_type))
    f, _ = create_cachefd("Autounattend.xml")
    f.write(template.render(config))  # pylint: disable=no-member
    f.close()


def prepare_packer_template(config, template_name):
    """
    Prepares a packer template JSON file according to configuration and writes
    it into a temporary location where packer later expects it.

    Uses jinja2 template syntax to generate the resulting JSON file.
    Templates are in templates/ and snippets in templates/snippets/.
    """
    try:
        resource_stream(
            __name__, "templates/{}.json".format(template_name)
        )
    except FileNotFoundError:
        print("Template doesn't exist: {}".format(template_name))
        sys.exit(2)

    filepath = resource_filename(__name__, "templates/")
    env = Environment(
        loader=FileSystemLoader(filepath),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("{}.json".format(template_name))

    # write to temporary file
    f, _ = create_cachefd("{}.json".format(template_name))
    packer_config = template.render(config)  # pylint: disable=no-member
    f.write(packer_config)
    f.close()

    if DEBUG:
        print("Generated configuration file for packer: {}".format(f.name))

    return f.name


def _prepare_vagrantfile(config, source, fd_dest):
    """
    Creates Vagrantfile based on a template using the jinja2 engine. Used for
    spin and also for the packer box Vagrantfile. Based on templates in
    vagrantfiles/.
    """
    filepath = resource_filename(__name__, "vagrantfiles/")
    env = Environment(loader=FileSystemLoader(filepath))
    template = env.get_template(source)

    fd_dest.write(template.render(config))  # pylint: disable=no-member
    fd_dest.close()


def prepare_config(args):
    """
    Prepares Malboxes configuration and merge with Packer template configuration

    Packer uses a configuration in JSON so we decided to go with JSON as well.
    However since we have features that should be easily "toggled" by our users
    I wanted to add an easy way of "commenting out" or "uncommenting" a
    particular feature. JSON doesn't support comments. However JSON's author
    gives a nice suggestion here[1] that I will follow.

    In a nutshell, our configuration is Javascript, which when minified gives
    JSON and then it gets merged with the selected template.
    """
    # If config does not exist, copy default one
    config_file = os.path.join(DIRS.user_config_dir, "config.js")
    if not os.path.isfile(config_file):
        print(
            "Default configuration doesn't exist. Populating one: {}".format(
                config_file
            )
        )
        shutil.copy(resource_filename(__name__, "config-example.js"), config_file)

    # Open config file
    if args.config is not None:
        config_file = open(args.config, "r")
    else:
        config_file = open(config_file, "r")

    # Load config
    config = load_config(config_file, args.template)

    # Get current template prefix
    prefix = "_".join(args.template.split("_")[:-1])

    # Set default settings if not specifically defined in config
    config = default_settings(config)

    # Check if required fields are set in config
    required_settings(config, prefix, config_file.name)

    if DEBUG:
        print("Computer name: {}".format(config["computername"]))
        print("Username: {}".format(config["username"]))
        print("Password: {}".format(config["password"]))

    # Overwrite and load correct profile
    if "profile" in config.keys() and args.profile is not None:
        print(
            "Overwriting profile: {} with profile: {}".format(
                config["profile"], args.profile
            )
        )

    generate_unique_vmname(config, args.template)

    global CURRENT_VM_DIR
    CURRENT_VM_DIR = os.path.join(VM_DIR_BASE, config["vm_name"])

    if not os.path.exists(CURRENT_VM_DIR):
        os.makedirs(CURRENT_VM_DIR)
    else:
        print("VM folder already exists. {}".format(CURRENT_VM_DIR))

        if not args.force:
            print("Use: `$ malboxes build <vm_name> --force` to override directory")
            sys.exit(2)
        else:
            shutil.rmtree(CURRENT_VM_DIR)
            os.makedirs(CURRENT_VM_DIR)

    if DEBUG:
        print("CURRENT_VM_DIR is: {}".format(CURRENT_VM_DIR))

    # add packer required variables
    # Note: Backslashes are replaced with forward slashes (Packer on Windows)
    config["cache_dir"] = CURRENT_VM_DIR.replace("\\", "/")
    config["dir"] = resource_filename(__name__, "").replace("\\", "/")
    config["template_name"] = args.template
    config["config_dir"] = DIRS.user_config_dir.replace("\\", "/")

    # Hide vm artifacts
    if config["hypervisor"] == "virtualbox":
        # Add hide artifacts startup script
        if config["hide_vm_artifacts"] == "true":
            filename = resource_filename(
                __name__, "scripts/windows/virtualbox_hide_artifacts.ps1"
            )
            dest = "$env:HOMEDRIVE\\hide_vm_artifacts.ps1"
            onstartup_script, task_name = onstartup_powershell_inline(filename)
            config["onstartup_script"].append(onstartup_script)
            print(
                "Added on_startup_script: src: {} dest: {} task_name: {}".format(
                    filename, dest, task_name
                )
            )

    # Parse profile config and load it into the config dict
    if args.profile is not None:
        config["profile"] = args.profile
        config = prepare_profile(args.template, config)
    elif "profile" in config.keys():
        config = prepare_profile(args.template, config)

    if config["cleanup"] == "true":
        filename = resource_filename(__name__, "scripts/windows/cleanup.ps1")
        onstartup_script, task_name = onstartup_powershell_inline(filename, "cleanup")
        config["onstartup_script"].append(onstartup_script)
        print(
            "Added on_startup_script: src: {} task_name: {}".format(
                filename, task_name
            )
        )
    else:
        print("No cleanup")

    if config["winrm"] == "false":
        filename = resource_filename(__name__, "scripts/windows/disable_winrm.ps1")
        onstartup_script, task_name = onstartup_powershell_inline(filename, "disable_winrm")
        config["onstartup_script"].append(onstartup_script)
        print(
            "Added on_startup_script: src: {} task_name: {}".format(
                filename, task_name
            )
        )

    if config["generate_random_files"] == "true":
        filepath = resource_filename(__name__, "scripts/windows/add_to_recent_files.cs")
        config["upload_compile_execute"].append(
            onstartup_folder_csharp(filepath)
            )

    if config["set_static_ip"] == "true":
        filepath = resource_filename(__name__, "scripts/windows/")

        fd, src_path = create_cachefd("set_static_ip.ps1")

        print("Set static ip file: {}".format(src_path))

        env = Environment(loader=FileSystemLoader(filepath))
        template = env.get_template("set_static_ip.ps1")

        template_vars = {
                "guest_ip": config["guest_ip"],
                "gateway_ip": config["gateway_ip"],
                "netmask": config["netmask"],
                "dnsserver_ip": config["dnsserver_ip"]
        }

        fd.write(template.render(template_vars))
        fd.close()

        print("Static ip path: {}".format(src_path))

        script, _ = onstartup_powershell_inline(src_path, "set_static_ip")
        config["onstartup_script"].append(script)

    # Download ISO if it is missing
    download_iso(config, prefix)

    # Generate Packer template
    packer_tmpl = prepare_packer_template(config, args.template)

    # merge/update with template config
    with open(packer_tmpl, "r") as f:
        try:
            config.update(json.loads(f.read()))
        except json.decoder.JSONDecodeError as ex:
            print("Error in packer template {}: {}".format(packer_tmpl, ex))
            sys.exit(2)

    return config, packer_tmpl


def generate_unique_vmname(config, template):
    # Generate unique VM name
    if config["hypervisor"] == "virtualbox":
        config["vm_name"] = generate_vm_name_virtualbox(config, template)

    else:
        if "vm_name" not in config.keys():
            config["vm_name"] = "{}_{}".format(template, randomString(6))


def required_settings(config, prefix, config_path):
    """Check if required fields are set in config"""

    if "{}_iso_name".format(prefix) not in config.keys():
        print("Error: '{}_iso_name' are not set in {}".format(prefix, config_path))
        sys.exit(2)

    if "{}_checksum".format(prefix) not in config.keys():
        print("Error: '{}_checksum' are not set in {}".format(prefix, config_path))
        sys.exit(2)

    if config["set_static_ip"] == "true":
        if "guest_ip" not in config.keys() or \
                "gateway_ip" not in config.keys() or \
                "netmask" not in config.keys():
            print("if set_static_ip is enabled following fields have to be set:")
            print("guest_ip, gateway_ip, netmask")
            sys.exit(2)

    if config["cleanup"] == "true" and config["flare_vm"] == "true":
        print("Config option 'cleanup: true' is not compatible with 'flare_vm: true'")
        sys.exit(2)


def default_settings(config):
    """Set default settings if not specifically defined in config"""

    default = {
        "win7_64_user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0",
        "win10_64_user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0",
        "hypervisor": "virtualbox",
        "username": randomString(8),
        "password": randomString(14),
        "computername": randomString(8),
        "iso_dir": os.path.join(DIRS.user_cache_dir, "iso"),
        "mac_address_nat": random_mac(),
        "mac_address_hostonly": random_mac(),
        "cpus": "2",
        "memory": "4096",
        "vram": "128",
        "skip_export": "true",
        "keep_registered": "true",
        "hide_vm_artifacts": "true",
        "guestadditions": "true",
        "windows_firewall": "true",
        "windows_updates": "false",
        "windows_defender": "false",
        "windows_testsigning": "false",
        "disk_size": "114441",  # 120 GB
        "choco_packages": "",
        "extra_choco_packages": "",
        "input_locale": "en-EN",
        "trial": "true",
        "profile": "default",
        "cleanup": "false",
        "onstartup_script": [],
        "upload_execute": [],
        "upload_compile_execute": [],
        "upload_onstartup": [],
        "screen_width": "1600",
        "screen_height": "1200",
        "set_static_ip": "false",
        "guest_ip": "",
        "netmask": "",
        "gateway_ip": "",
        "dnsserver_ip": "",
        "secondary_dnsserver_ip": "",
        "openssh_server": "false",
        "winrm": "false",
        "flare_vm": "false",
        "generate_random_files": "true",
        "choco_source": "https://chocolatey.org/api/v2",
        "flare_source": "https://www.myget.org/F/flare/api/v2",
        "enable_flare_source": "false"
    }
    default.update(config)

    return default


def get_default_machine_folder():
    """Gets the path to the default machine folder"""

    if shutil.which("VBoxManage") is None:
        print("VirtualBox and VBoxManage has to be installed")
        sys.exit(2)

    command = ["VBoxManage", "list", "systemproperties"]
    settings = run_background(command)

    default_path = ""
    r = re.compile("Default machine folder:          ")

    try:
        for line in settings.split("\n"):
            if line != "" and line is not None:
                res = r.search(line)

                if res is not None:
                    default_path = line[res.span(0)[1]:]
                    break

    except AttributeError as ex:
        print(
            "Parsing command {} failed. Did the command output change?".format(command)
        )
        print("Command output: {}".format(settings))
        raise ex

    return default_path


def generate_vm_name_virtualbox(config, template):
    """Generates a vm name. If it already exists in VirtualBox append a _<num> to the name."""

    if shutil.which("VBoxManage") is None:
        print("VirtualBox and VBoxManage has to be installed")
        sys.exit(2)

    command = ["VBoxManage", "list", "vms"]
    vms = run_background(command)
    vms_t = ""

    r = re.compile(" {([a-z0-9]{8}-){1}([a-z0-9]{4}-){3}([a-z0-9]{12}){1}}")

    try:
        for line in vms.split("\n"):
            if line != "" and line is not None:
                vms_t += line[: r.search(line).span(0)[0]] + ", "

    except AttributeError as ex:
        print(
            "Parsing command {} failed. Did the command output change?".format(command)
        )
        print("Command output: {}".format(vms))
        raise ex

    if "vm_name" not in config.keys():
        if "profile" not in config.keys():
            vm_name = template
        else:
            vm_name = "{}_{}".format(template, config["profile"])
    else:
        vm_name = config["vm_name"]

    counter = 0
    while True:

        result = "{}_{}".format(vm_name, counter)

        counter += 1
        if result not in vms_t:
            break
    return result


def set_vm_description_virtualbox(vm_name, description):
    """Adds a decription to the vm"""

    if shutil.which("VBoxManage") is None:
        print("VirtualBox and VBoxManage has to be installed")
        sys.exit(2)

    command = ["VBoxManage", "modifyvm", vm_name, "--description", description]
    run_background(command)


def download_iso(config, prefix):
    """Downloads the appropriate ISO image"""

    iso_dir = config["iso_dir"]
    iso_name = config["{}_iso_name".format(prefix)]
    iso_path = os.path.join(iso_dir, iso_name)

    # Check if ISO directory exists
    if not os.path.exists(iso_dir):
        print("Iso dir doesn't exist creating it")
        os.mkdir(iso_dir)

    # If ISO doesn't exist download it
    if (
        not os.path.exists(iso_path)
        and "{}_iso_download".format(prefix) in config.keys()
    ):
        print("Starting to download to: {}".format(iso_path))

        #  Default user agent
        #user_agent = "Wget/1.19.5 (linux-gnu)"
        user_agent = config["{}_user_agent".format(prefix)]

        try:
            # Download file from url
            url = config["{}_iso_download".format(prefix)]
            r = requests.get(
                url,
                allow_redirects=True,
                headers={"User-Agent": user_agent},
                stream=True,
            )

            # Total size in bytes.
            total_size = int(r.headers.get("content-length", 0))
            block_size = 8024  # Max memory allocation in bytes
            wrote = 0

            if DEBUG:
                print("Content-Length: {}".format(total_size))

            # Write ISO
            with open(iso_path, "wb") as f:
                # Display download bar
                pbar = tqdm(total=total_size, unit="B", unit_scale=True)
                for chunk in r.iter_content(block_size):
                    if chunk:
                        pbar.update(len(chunk))
                        wrote = wrote + len(chunk)
                        f.write(chunk)
        except (KeyboardInterrupt, requests.RequestException) as ex:
            pbar.close()
            print("Stopped downloading because of: {}. Removing file...".format(ex))
            os.remove(iso_path)

        # Error check
        if total_size != 0 and wrote != total_size:
            print("Downloaded file didn't reach its total size. Exiting.")
            sys.exit(2)


def load_config(config_file, template):
    """Loads the minified JSON config. Returns a dict."""

    try:
        content = jsmin(config_file.read())
        # minify then load as JSON
        config = json.loads(content)
    except json.JSONDecodeError as ex:
        print(
            "An error occurred on parsing the json in {}: {}".format(
                config_file.name, ex
            )
        )
        fd, _ = create_cachefd("minified-config.json")
        fd.write(content)
        print("Minified file can be found at: {}".format(fd.name))
        sys.exit(2)

    if "tools_path" in config.keys():
        config["tools_path"] = os.path.expanduser(config["tools_path"])

    if "iso_dir" in config.keys():
        config["iso_dir"] = os.path.expanduser(config["iso_dir"])

    return config


def load_profile(profile_name):
    filename = os.path.join(
        DIRS.user_config_dir.replace("\\", "/"),
        "profiles",
        "{}.js".format(profile_name),
    )

    """Loads the profile, minifies it and returns the content."""
    with open(filename, "r") as profile_file:
        try:
            content = jsmin(profile_file.read())
            profile = json.loads(content)

        except json.JSONDecodeError as ex:
            print(
                "An error occurred on parsing the json in {}: {}".format(filename, ex)
            )
            fd, _ = create_cachefd("minified-profile.json")
            fd.write(content)
            print("Enable debug mode (-d) to have the minified json in {}".format(fd.name))
            sys.exit(2)

    return profile


def _get_os_type(config):
    """OS Type is extracted from template json config.
       For older hypervisor compatibility, some values needs to be updated here.
    """
    _os_type = config["builders"][0]["guest_os_type"].lower()
    if config["hypervisor"] == "vsphere":
        if _os_type == "windows8":
            _os_type = "windows10"
        elif _os_type == "windows8-64":
            _os_type = "windows10_64"

    return _os_type


def create_cachefd(filename):
    tempfiles.append(filename)
    global CURRENT_VM_DIR
    file_path = os.path.join(CURRENT_VM_DIR, filename)

    # if os.path.exists(file_path):
    #     raise RuntimeError("file {} already exists!".format(file_path))

    return open(file_path, "w"), file_path


def cleanup():
    """Removes temporary files. Keep them in debug mode."""
    if not DEBUG:
        for f in tempfiles:
            os.remove(os.path.join(CURRENT_VM_DIR, f))


def run_background(command, env=None):
    if DEBUG:
        print("DEBUG: Executing {}".format(command))

    cmd_env = os.environ.copy()
    if env is not None:
        cmd_env.update(env)

    p = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        env=cmd_env,
    )
    output = p.stdout.decode("utf-8")
    return output


def run_foreground(command, env=None):
    if DEBUG:
        print("DEBUG: Executing {}".format(command))

    cmd_env = os.environ.copy()
    if env is not None:
        cmd_env.update(env)

    p = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=cmd_env
    )
    try:
        for line in iter(p.stdout.readline, b""):
            print(line.rstrip().decode("utf-8"))

    # send Ctrl-C to subprocess
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        for line in iter(p.stdout.readline, b""):
            print(line.rstrip().decode("utf-8"))
        raise

    finally:
        p.wait()
        return p.returncode


def run_packer(packer_tmpl, args):
    print("Starting packer to generate the VM")
    print("----------------------------------")

    prev_cwd = os.getcwd()
    os.chdir(CURRENT_VM_DIR)
    print("Changed to {}".format(os.getcwd()))
    start_time = time.time()

    try:
        # packer or packer-io?
        binary = "packer-io"
        if shutil.which(binary) is None:
            binary = "packer"
            if shutil.which(binary) is None:
                print(
                    "packer not found. Install it: https://www.packer.io/docs/install/index.html"
                )
                return 254

        # run packer with relevant config minified
        configfile = os.path.join(DIRS.user_config_dir, "config.js")
        with open(configfile, "r") as config:
            try:
                f, _ = create_cachefd("packer_var_file.json")
                f.write(jsmin(config.read()))
                f.close()

            except json.decoder.JSONDecodeError as ex:
                print("Error in config.json {}: {}".format(packer_tmpl, ex))
                sys.exit(2)

        flags = ["-var-file={}".format(f.name)]

        packer_cache_dir = os.getenv("PACKER_CACHE_DIR", CURRENT_VM_DIR)
        special_env = {"PACKER_CACHE_DIR": packer_cache_dir}
        special_env["TMPDIR"] = CURRENT_VM_DIR
        if DEBUG:
            special_env["PACKER_LOG"] = "1"
            special_env["PACKER_LOG_PATH"] = PACKER_LOG_PATH
            flags.append("-on-error=abort")

        if args.force:
            flags.append("-force")

        cmd = [binary, "build"]
        cmd.extend(flags)
        cmd.append(packer_tmpl)
        ret = run_foreground(cmd, special_env)

    finally:
        os.chdir(prev_cwd)

    end_time = time.time()
    print("----------------------------------")
    print("packer completed with return code: {}".format(ret))
    print(
        "Total running time of packer: {0:.2f} minutes".format(
            (end_time - start_time) / 60
        )
    )
    return ret


def add_box(config, args):
    print("Adding box into vagrant")
    print("--------------------------")

    box = config["post-processors"][0]["output"]
    box = os.path.join(CURRENT_VM_DIR, box)
    box = box.replace("{{user `name`}}", args.template)

    flags = ["--name={}".format(args.template)]
    if args.force:
        flags.append("--force")

    cmd = ["vagrant", "box", "add"]
    cmd.extend(flags)
    cmd.append(box)
    ret = run_foreground(cmd)

    print("----------------------------")
    print("vagrant box add completed with return code: {}".format(ret))
    return ret


def default(parser, args):
    parser.print_help()
    print("\n")
    list_templates(parser, args)
    sys.exit(2)


def list_templates(parser, args):
    print("supported templates:\n")

    filepath = resource_filename(__name__, "templates/")
    for f in sorted(glob.glob(os.path.join(filepath, "*.json"))):
        m = re.search(r"templates[\/\\](.*).json$", f)
        print(m.group(1))
    print()


def build(parser, args):
    print("Generating configuration files...")
    config, packer_tmpl = prepare_config(args)
    prepare_autounattend(config)
    print("Configuration files are ready")

    # TODO: Remove
    with open("/tmp/malboxes-vars.json", "w") as f:
        f.write(json.dumps(config))

    ret = run_packer(packer_tmpl, args)

    if ret == 0:
        description = {
            "username": config["username"],
            "password": config["password"],
            "computername": config["computername"],
        }

        if config["set_static_ip"] == "true":
            description["static_ip"] = config["guest_ip"]

        # Set Username and password as description in VM
        set_vm_description_virtualbox(config["vm_name"], json.dumps(description))

    if ret != 0:
        print("Packer failed. Build failed. Exiting...")
        sys.exit(2)


def spin(parser, args):
    """
    Creates a Vagrantfile meant for user-interaction in the current directory.
    """
    if os.path.isfile("Vagrantfile"):
        print("Vagrantfile already exists. Please move it away. Exiting...")
        sys.exit(2)

    config, _ = prepare_config(args)

    config["template"] = args.template
    config["name"] = args.name

    print("Creating a Vagrantfile")
    if config["hypervisor"] == "virtualbox":
        with open("Vagrantfile", "w") as f:
            _prepare_vagrantfile(config, "analyst_single.rb", f)
    elif config["hypervisor"] == "vsphere":
        with open("Vagrantfile", "w") as f:
            _prepare_vagrantfile(config, "analyst_vsphere.rb", f)
    print(
        "Vagrantfile generated. You can move it in your analysis directory "
        "and issue a `vagrant up` to get started with your VM."
    )


def prepare_profile(template, config):
    """Loads the profile and returns it as JSON dict"""

    profile_name = config["profile"]

    profile_filename = os.path.join(
        DIRS.user_config_dir, "profiles", "{}.js".format(profile_name)
    )

    # if profile file doesn't exist, populate it from default
    if not os.path.isfile(profile_filename):
        shutil.copy(resource_filename(__name__, "profile-example.js"), profile_filename)
        print(
            "WARNING: A profile was specified but was not found on disk. Copying a default one."
        )

    profile = load_profile(profile_name)

    # To register inline powershell to task scheduler
    if "onstartup_powershell_inline" in profile.keys():
        for script in profile["onstartup_powershell_inline"]:
            src = script["src"]

            if "task_name" in script.keys():
                onstartup_script, task_name = onstartup_powershell_inline(src, script["task_name"])
            else:
                onstartup_script, task_name = onstartup_powershell_inline(src)

            print(
                "Added onstartup_powershell_inline: src: {} task_name: {}".format(
                    src, task_name
                )
            )
            config["onstartup_script"].append(onstartup_script)

    # To register powershell file to task scheduler
    if "onstartup_powershell_file" in profile.keys():
        for script in profile["onstartup_powershell_file"]:
            src = script["src"]

            if "dest" in script.keys():
                onstartup_script, task_name = onstartup_powershell_file(src, script["dest"])
                print(
                    "Added onstartup_powershell_file: src: {} dest: {} task_name: {}".format(
                        src, script["dest"], task_name
                    )
                )
                config["onstartup_script"].append(onstartup_script)
            else:
                print("'dest' key missing  in onstartup_powershell_file")
                sys.exit(2)

    # onstartup_csharp(src, args, task_name=None):
    if "win7" in template:
        filepath = resource_filename(__name__, "scripts/windows/")

        fd, xml_src_path = create_cachefd("Startup-folder_setscreenres.cs")

        print("Csharp file: {}".format(xml_src_path))

        env = Environment(loader=FileSystemLoader(filepath))
        template = env.get_template("set_resolution_win7.cs")

        template_vars = {
                "screen_width": config["screen_width"],
                "screen_height": config["screen_height"]
        }

        fd.write(template.render(template_vars))

        onstartup_script = onstartup_folder_csharp(fd.name)
        print(
            "Added on_startup_folder_csharp: src: {} ".format(
                fd.name
            )
        )
        config["onstartup_script"].append(onstartup_script)

    fd, _ = create_cachefd("profile-{}.ps1".format(profile_name))
    # Extra Choco Packages tag in profile
    if "extra_choco_packages" in profile.keys():
        package(profile_name, profile["extra_choco_packages"], fd)

    # Directory tag in profile
    if "directory" in profile.keys():
        for dir_mod in profile["directory"]:
            directory(profile_name, dir_mod["modtype"], dir_mod["dirpath"], fd)

    # Shortcut tag in profile
    if "shortcut" in profile.keys():
        shortcut_function(fd)
        for shortcut_mod in profile["shortcut"]:
            if "arguments" not in shortcut_mod:
                shortcut_mod["arguments"] = None
            shortcut(
                shortcut_mod["dest"],
                shortcut_mod["target"],
                shortcut_mod["arguments"],
                fd,
            )
    fd.close()

    if "upload_onstartup" in profile.keys():
        for exec_mod in profile["upload_onstartup"]:
            if "src" in exec_mod:

                src = os.path.expanduser(exec_mod["src"])
                upload_onstartup = [
                    {
                        "type": "file",
                        "source": src,
                        "destination": "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{}"
                        .format(os.path.basename(exec_mod["src"]))
                    }
                ]

                config["upload_onstartup"].append(upload_onstartup)
            else:
                print("Error: upload_onstartup directive in profile needs a src key and a args key")
                sys.exit(2)

    if "upload_execute" in profile.keys():
        for exec_mod in profile["upload_execute"]:
            if "src" in exec_mod and "args" in exec_mod:
                config["upload_execute"].append(
                        upload_execute(config, exec_mod["src"], exec_mod["args"])
                        )
            else:
                print("Error: exec directive in profile needs a src key and a args key")
                sys.exit(2)

    if "upload_compile_execute" in profile.keys():
        for compile_mod in profile["upload_compile_execute"]:
            if "src" in compile_mod and "args" in compile_mod:
                config["upload_compile_execute"].append(
                        upload_compile_execute(compile_mod["src"], compile_mod["args"])
                        )
            else:
                print("Error: compile directive in profile needs a src key and a args key")
                sys.exit(2)

    # Overwrite tag in profile
    if "overwrite" in profile.keys():
        if "hypervisor" in profile["overwrite"].keys():
            print("The hypervisor key can't be orverriden in profile!")
            print("To use a different hypervisor define a different config with -c")
            sys.exit(2)
        config.update(profile["overwrite"])

    return config


def upload_execute(config, src, args):
    """
    src --> Path to executable
    args --> args given as input to executable
    """

    src = os.path.expanduser(src)

    if not os.path.exists(src):
        print("File not found: {}".format(src))
        sys.exit(2)

    filename, file_extension = os.path.splitext(src)

    dest_file_name = "{}{}".format(randomString(10), file_extension)
    dest = "$env:TEMP\\{}".format(dest_file_name)

    exec_script = [
        {"type": "file", "source": src, "destination": dest},
        {
            "type": "powershell",
            "inline": [
                '& "{}" {}'.format(dest, args),
            ],
        },
    ]

    return exec_script


def upload_compile_execute(src, args):
    """
    src --> Path to executable
    args --> args given as input to executable
    """

    src = os.path.expanduser(src)

    if not os.path.exists(src):
        print("File not found: {}".format(src))
        sys.exit(2)

    filename, file_extension = os.path.splitext(src)

    if file_extension != ".cs":
        print("File extension in upload_compile_execute has to be .cs!")
        sys.exit(2)

    # Test if the csharp is correct
    test_compile_csharp(src)

    rand_file_name = "{}".format(randomString(10))
    dest_source = "$env:TEMP\\{}.cs".format(rand_file_name)
    dest_compiled = "$env:TEMP\\{}.exe".format(rand_file_name)

    exec_script = [
        {"type": "file", "source": src, "destination": dest_source},
        {
            "type": "powershell",
            "inline": [
                'Add-Type -outputtype consoleapplication -outputassembly {} -Path "{}"'.format(
                    dest_compiled, dest_source),
                '& "{}" {}'.format(dest_compiled, args),
            ],
        },
    ]

    return exec_script


def test_compile_csharp(src):
    src = os.path.expanduser(src)

    try:
        if sys.platform.startswith("win32"):

            if shutil.which("powershell") is None:
                print("WARNING: To check for CSharp errors Powershell has to be installed locally")
                print("Executable 'powershell' not found.")
                return

            run_background(["powershell", "-Command", "Add-Type", "-Path", "'{}'".format(src)])
        else:
            if shutil.which("pwsh") is None:
                print("WARNING: To check for CSharp errors Powershell has to be installed locally.")
                print("Executable 'pwsh' not found.")
                return

            run_background(["pwsh", "-Command", "Add-Type", "-Path", "'{}'".format(src)])

    except subprocess.CalledProcessError as ex:
        print("CSharp compile error in: {}".format(src))
        print(ex.output)
        sys.exit(2)


def onstartup_folder_csharp(src, task_name=None):
    src = os.path.expanduser(src)

    if task_name is None or task_name == "":
        task_name = randomString(10)

    if not os.path.exists(src):
        print("File not found: {}".format(src))
        sys.exit(2)

    filename, file_extension = os.path.splitext(src)

    if file_extension != ".cs":
        print("File extension in upload_compile_execute has to be .cs!")
        sys.exit(2)

    rand_file_name = "{}".format(randomString(10))
    dest_source = "$env:TEMP\\{}.cs".format(rand_file_name)
    dest_compiled = "$env:APPDATA\\Microsoft\\Windows\\'Start Menu'\\Programs\\Startup\\{}.exe".format(rand_file_name)

    test_compile_csharp(src)

    compile_script = [
        {"type": "file", "source": src, "destination": dest_source},
        {
            "type": "powershell",
            "inline": [
                "Add-Type -outputtype consoleapplication -outputassembly {} -Path {}".format(
                    dest_compiled, dest_source),
                "Remove-Item $env:APPDATA\\Microsoft\\Windows\\'Start Menu'\\Programs\\Startup\\{}.pdb".format(rand_file_name)
            ],
        },
    ]

    return compile_script


def onstartup_csharp(src, args, task_name=None):
    """
    Compiles and registers the csharp script to startup
    src -> Path to a csharp script
    args -> Arguemtns to call the csharp script
    task_name -> Name of the task
    """

    src = os.path.expanduser(src)

    if task_name is None or task_name == "":
        task_name = randomString(10)

    if not os.path.exists(src):
        print("File not found: {}".format(src))
        sys.exit(2)

    filename, file_extension = os.path.splitext(src)

    if file_extension != ".cs":
        print("File extension in upload_compile_execute has to be .cs!")
        sys.exit(2)

    # Test if the csharp is correct
    test_compile_csharp(src)

    rand_file_name = "{}".format(randomString(10))
    dest_source = "$env:TEMP\\{}.cs".format(rand_file_name)
    dest_compiled = "$env:TEMP\\{}.exe".format(rand_file_name)

    compile_script = [
        {"type": "file", "source": src, "destination": dest_source},
        {
            "type": "powershell",
            "inline": [
                "Add-Type -outputtype consoleapplication -outputassembly {} -Path {}".format(
                    dest_compiled, dest_source),
                "Remove-Item $env:TEMP\\{}.pdb".format(rand_file_name)
            ],
        },
    ]

    xml_dest = "$env:TEMP/{}.xml".format(task_name)

    filepath = resource_filename(__name__, "scripts/windows")
    fd, xml_src_path = create_cachefd("on_startup_csharp-{}.xml".format(task_name))

    env = Environment(loader=FileSystemLoader(filepath))
    template = env.get_template("task_scheduler_csharp.xml")

    template_vars = {
        "execute": '%TEMP%\{}.exe {}'.format(rand_file_name, args),
        "author": randomString(8),
        "date": datetime.datetime.now().replace(microsecond=0).isoformat()
    }

    fd.write(template.render(template_vars))

    startup_script = [
        {"type": "file", "source": xml_src_path, "destination": xml_dest},
        {
            "type": "powershell",
            "inline": [
                "Schtasks /create /ru 'System' /tn {} /xml {}".format(
                    task_name, xml_dest
                ),
                "Remove-Item {}".format(xml_dest),
            ],
        },
    ]

    fd.close()
    return (compile_script + startup_script, task_name)


def onstartup_powershell_inline(src, task_name=None):
    """
    Adds a base64 encoded powershell script to the task scheduler
    src -> Path to powershell script
    task_name -> Name of the task
    """

    src = os.path.expanduser(src)

    if task_name is None or task_name == "":
        task_name = randomString(10)

    xml_dest = "$env:TEMP/{}.xml".format(task_name)

    filepath = resource_filename(__name__, "scripts/windows")
    fd, xml_src_path = create_cachefd("on_startup-{}.xml".format(task_name))

    env = Environment(loader=FileSystemLoader(filepath))
    template = env.get_template("task_scheduler_inline.xml")

    # Read powershell and convert to base64
    with open(src, "r") as f:
        content = f.read()
        base64_cmd = base64.b64encode(content.encode("UTF-16LE")).decode()

        if len(base64_cmd) > 32500:
            print("Powershellscript is too big. Windows doesn't support arguments that long. Max size is {}. Src: {}".format(
                32500, src))
            sys.exit(2)

    template_vars = {
        "base64_cmd": base64_cmd,
        "author": randomString(8),
        "date": datetime.datetime.now().replace(microsecond=0).isoformat()
    }

    fd.write(template.render(template_vars))

    startup_script = [
        {"type": "file", "source": xml_src_path, "destination": xml_dest},
        {
            "type": "powershell",
            "inline": [
                "Schtasks /create /ru 'System' /tn {} /xml {}".format(
                    task_name, xml_dest
                ),
                "Remove-Item {}".format(xml_dest),
            ],
        },
    ]

    fd.close()
    return (startup_script, task_name)


def onstartup_powershell_file(src, dest=None, task_name=None):
    """ Returns a tuple where the first entry is a list with a dict
    with the configuration for packer to create a startup
    script and the second one is the name of the task
    """
    src = os.path.expanduser(src)

    if task_name is None or task_name == "":
        task_name = randomString(10)

    xml_dest = "$env:TEMP/{}.xml".format(task_name)

    filepath = resource_filename(__name__, "scripts/windows")
    fd, xml_src_path = create_cachefd("on_startup-{}.xml".format(task_name))

    env = Environment(loader=FileSystemLoader(filepath))
    template = env.get_template("task_scheduler_file.xml")

    template_vars = {
        "pwsh_script": dest,
        "author": randomString(8),
        "date": datetime.datetime.now().replace(microsecond=0).isoformat()
    }

    fd.write(template.render(template_vars))
    fd.close()

    startup_script = [
        {"type": "file", "source": src, "destination": dest},
        {"type": "file", "source": xml_src_path, "destination": xml_dest},
        {
            "type": "powershell",
            "inline": [
                "Schtasks /create /ru 'System' /tn {} /xml {}".format(
                    task_name, xml_dest
                ),
                "Remove-Item {}".format(xml_dest),
            ],
        },
    ]

    return (startup_script, task_name)


def directory(profile_name, modtype, dirpath, fd):
    """ Adds the directory manipulation commands to the profile."""
    if modtype == "add":
        command = "New-Item"
        line = '{0} -Path "{1}" -Type directory\r\n'.format(command, dirpath)
        print("Adding directory: {}".format(dirpath))
    elif modtype == "delete":
        command = "Remove-Item"
        line = '{0} -Path "{1}"\r\n'.format(command, dirpath)
        print("Removing directory: {}".format(dirpath))
    else:
        print("Directory modification type invalid.")
        print("Valid ones are: add, delete.")

    fd.write(line)


def package(profile_name, package_name, fd):
    """ Adds a package to install with Chocolatey."""
    line = "choco install {} -y\r\n".format(package_name)
    print("Adding Chocolatey package: {}".format(package_name))

    fd.write(line)


def shortcut_function(fd):
    """ Add shortcut function to the profile """
    filename = resource_filename(__name__, "scripts/windows/add-shortcut.ps1")
    with open(filename, "r") as add_shortcut_file:
        fd.write(add_shortcut_file.read())
        add_shortcut_file.close()


def shortcut(dest, target, arguments, fd):
    """ Create shortcut on Desktop """
    if arguments is None:
        line = 'Add-Shortcut "{0}" "{1}"\r\n'.format(target, dest)
        print("Adding shortcut {}: {}".format(dest, target))
    else:
        line = 'Add-Shortcut "{0}" "{1}" "{2}"\r\n'.format(target, dest, arguments)
        print(
            "Adding shortcut {}: {} with arguments {}".format(dest, target, arguments)
        )
    fd.write(line)


def random_mac():
    return "020000%02x%02x%02x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def randomString(stringLength):
    """Generate a random string with the combination of lowercase and uppercase letters """
    letters = string.ascii_letters
    return "".join(secrets.choice(letters) for i in range(stringLength))


def main():
    global DEBUG

    try:
        # Start malboxes
        parser, args = initialize()

        if args.ssh:
            ssh_into_vm(args.ssh, args.ip)
            sys.exit(0)

        if args.debug:
            DEBUG = True
            print("NOTE: Running in DEBUG mode!")
            print("VM_DIR_BASE: {}".format(VM_DIR_BASE))

        args.func(parser, args)

    finally:
        cleanup()


if __name__ == "__main__":
    main()
