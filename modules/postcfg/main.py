#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <http://github.com/calamares> ===
#
#   Copyright 2014 - 2019, Philip Müller <philm@manjaro.org>
#   Copyright 2016, Artoo <artoo@manjaro.org>
#
#   Calamares is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Calamares is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Calamares. If not, see <http://www.gnu.org/licenses/>.

import libcalamares
import subprocess

from shutil import copy2
from distutils.dir_util import copy_tree
from os.path import join, exists
from libcalamares.utils import target_env_call
from libcalamares.utils import target_env_process_output
from libcalamares.utils import check_target_env_output

def pretty_name():
    return ("Misc post-install configurations")

status = ("Misc post-install configurations")

def pretty_status_message():
    return status

class ConfigController:
    def __init__(self):
        self.__root = libcalamares.globalstorage.value("rootMountPoint")

    @property
    def root(self):
        return self.__root

    def terminate(self, proc):
        target_env_call(['killall', '-9', proc])

    def copy_file(self, file):
        if exists("/" + file):
            copy2("/" + file, join(self.root, file))

    def copy_folder(self, source, target):
        if exists("/" + source):
            copy_tree("/" + source, join(self.root, target))

    def remove_pkg(self, pkg):
            libcalamares.utils.target_env_process_output(['xbps-remove', '-Ry', pkg])

    def umount(self, mp):
        subprocess.call(["umount", "-l", join(self.root, mp)])

    def mount(self, mp):
        subprocess.call(["mount", "-B", "/" + mp, join(self.root, mp)])

    def rmdir(self, dir):
        subprocess.call(["rm", "-Rf", join(self.root, dir)])

    def mkdir(self, dir):
        subprocess.call(["mkdir", "-p", join(self.root, dir)])

    def run(self):
        status = ("Removing CLI installer")
        if exists(join(self.root, "usr/sbin/void-installer")):
            libcalamares.utils.target_env_process_output(["rm", "-fv", "usr/sbin/void-installer"])

        if exists(join(self.root, "usr/sbin/cereus-installer")):
            libcalamares.utils.target_env_process_output(["rm", "-fv", "usr/sbin/cereus-installer"])

        status = ("Initializing package manager databases")
        if libcalamares.globalstorage.value("hasInternet"):
            libcalamares.utils.target_env_process_output(["xbps-install", "-Syy"])

        # Remove calamares
        status = ("Removing Calamares from target")
        self.remove_pkg("calamares-cereus")
        if exists(join(self.root, "usr/share/applications/calamares.desktop")):
            target_env_call(["rm", "-fv", "usr/share/applications/calamares.desktop"])

        # Remove Breeze if Plasma is not installed
        if exists(join(self.root, "usr/bin/startplasma-x11")):
            print("Plasma is installed, not removing Breeze")
        else:
            status = ("Removing Breeze")
            self.remove_pkg("breeze")

        # If Plasma or LXQt are installed, remove Qt5ct
        if exists(join(self.root, "usr/bin/startplasma-x11")):
            status = ("Removing Qt5ct")
            self.remove_pkg("qt5ct")
        elif exists(join(self.root, "usr/bin/startlxqt")):
            status = ("Removing Qt5ct")
            self.remove_pkg("qt5ct")
        
        # Remove Emptty if LightDM is present
        if exists(join(self.root, "etc/lightdm/lightdm.conf")):
            if exists(join(self.root, "usr/bin/emptty")):
                status = ("Removing Emptty")
                libcalamares.utils.target_env_process_output(["rm", "-fv" , "etc/runit/runsvdir/default/emptty"])
                libcalamares.utils.target_env_process_output(["rm" , "-rfv", "etc/emptty"])
                self.remove_pkg("emptty")

        # Copy skel to root
        status = ("Copying skel to root")
        self.copy_folder('etc/skel', 'root')

        # Update grub.cfg
        status = ("Updating GRUB")
        if exists(join(self.root, "usr/bin/update-grub")):
            libcalamares.utils.target_env_process_output(["update-grub"])

        # Enable 'menu_auto_hide' when supported in grubenv
        if exists(join(self.root, "usr/bin/grub-set-bootflag")):
            target_env_call(["grub-editenv", "-", "set", "menu_auto_hide=1", "boot_success=1"])

        # Enable plymouth
        status = ("Enabling Plymouth on target")
        libcalamares.utils.target_env_process_output(["plymouth-set-default-theme", "-R", "cereus_simply"])

        # Replace /etc/issue msg from live
        if exists(join(self.root, "etc/issue.new")):
            libcalamares.utils.target_env_process_output(["mv", "etc/issue.new", "etc/issue"])

        # If doas installed on target, enable it
        if exists(join(self.root, "usr/bin/doas")):
            doasconf = "permit nopass :root ||\npermit persist :wheel"
            with open(join(self.root, "etc/doas.conf"), 'w') as conf:
                conf.write(doasconf)

        # Override default XFCE wallpaper
        if exists(join(self.root, "usr/share/backgrounds/xfce/xfce-shapes.png")):
            libcalamares.utils.target_env_process_output(["rm", "-fv", "usr/share/backgrounds/xfce/xfce-shapes.png"])
            libcalamares.utils.target_env_process_output(["ln", "-frsv", "usr/share/backgrounds/wallpaper4.png", "usr/share/backgrounds/xfce/xfce-shapes.png"])

        # Mark current kernel as automatically installed (this allows to remove old LTS kernels as orphaned packages).
        libcalamares.utils.target_env_process_output(["xbps-pkgdb", "-m", "auto", "linux6.1"])

        # Remove linux-headers meta-package
        status = ("Removing linux-headers from target")
        libcalamares.utils.target_env_process_output(["xbps-remove", "-RFyv", "linux-headers"])
        ignorepkg = "ignorepkg=linux-headers"
        self.mkdir("etc/xbps.d/")
        with open(join(self.root, "etc/xbps.d/00-ignore.conf"), 'w') as conf:
            conf.write(ignorepkg)

        # Reconfigure all target packages to ensure everything is ok
        status = ("Reconfiguring all target packages")
        libcalamares.utils.target_env_process_output(["xbps-reconfigure", "-fa"])

def run():
    """ Misc post-install configurations """

    config = ConfigController()

    return config.run()
