#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import json
import libcalamares
import os
import subprocess
import re

import gettext

_ = gettext.translation(
    "calamares-python",
    localedir=libcalamares.utils.gettext_path(),
    languages=libcalamares.utils.gettext_languages(),
    fallback=True,
).gettext


cfghead = """# finix system configuration
# rebuild: sudo @@rebuildcmd@@ switch

{ config, pkgs, ... }:

{
  imports = [ ./hardware-configuration.nix ];

  finit.runlevel = 3;
  finit.services.nix-daemon.environment.CURL_CA_BUNDLE = config.security.pki.caBundle;
  services.nix-daemon.enable = true;
  services.nix-daemon.settings.experimental-features = [ "nix-command" "flakes" ];
  services.nix-daemon.settings.trusted-users = [ "root" "@wheel" ];

  services.dbus.enable = true;
  services.sysklogd.enable = true;
  services.polkit.enable = true;
  services.chrony.enable = true;
  services.bluetooth.enable = true;

  programs.sudo.enable = true;
  programs.bash.enable = true;
  hardware.graphics.enable = true;
  fonts.fontconfig.enable = true;
  fonts.enableDefaultPackages = true;

"""

cfgnixlowram = """  # low-RAM machine: one build at a time
  services.nix-daemon.settings.max-jobs = 1;
  services.nix-daemon.settings.cores = @@buildcores@@;

"""

cfgseatd = """  services.mdevd.enable = true;
  services.seatd.enable = true;

"""

cfgelogind = """  # plasma needs elogind, elogind needs the udev database
  services.udev.enable = true;
  services.elogind.enable = true;
  programs.xorg.package = pkgs.xorg-server.override { udev = pkgs.eudev; };

  services.polkit.extraConfig = ''
    polkit.addRule(function(action, subject) {
      if (subject.isInGroup("wheel") &&
          (action.id.indexOf("org.freedesktop.login1.power-off") == 0 ||
           action.id.indexOf("org.freedesktop.login1.reboot") == 0 ||
           action.id.indexOf("org.freedesktop.login1.suspend") == 0 ||
           action.id.indexOf("org.freedesktop.login1.hibernate") == 0)) {
        return polkit.Result.YES;
      }
    });
  '';

"""

cfgnet = """  # network: dhcpcd + iwd (iwctl for wifi)
  services.dhcpcd.enable = true;
  services.dhcpcd.extraArgs = [ "--noipv6rs" ];
  services.iwd.enable = true;
  programs.resolvconf.enable = true;
  programs.resolvconf.settings.name_servers_append = [ "1.1.1.1" "1.0.0.1" ];
  programs.resolvconf.settings.resolv_conf_options = [ "timeout:2" "attempts:2" ];
  programs.resolvconf.settings.libc_restart = "true";
  networking.hostName = "@@hostname@@";

"""

cfggreet = """  # login
  programs.regreet.enable = true;
  programs.regreet.compositor.environment.XDG_DATA_DIRS = "/run/current-system/sw/share";
  programs.regreet.settings.background = {
    path = "@@etcdir@@/wallpaper.png";
    fit = "Cover";
  };
  programs.regreet.settings.GTK.application_prefer_dark_theme = true;
  services.greetd.settings.terminal.vt = 1;
  services.getty.ttys = [ "tty2" "tty3" "tty4" "tty5" "tty6" ];

"""

cfgaudio = """  # audio
  programs.pipewire.enable = true;
  programs.pipewire.alsa.enable = true;
  programs.wireplumber.enable = true;
  services.rtkit.enable = true;
  users.groups.audio.gid = config.ids.gids.audio;

"""

NIXPKGS_REV = "e2587caef70cea85dd97d7daab492899902dbf5d"
FINIX_REV = "8a9b75a16b6f399e12d031dcd714a938af40c9b5"
NOCTALIA_REV = "3d7b9869950592ff7cf3704f6a53afb169d850db"
NVWM_REV = "58bfe34f14d532b6fdcac3149133cccd2e3bf653"
VXWM_REV = "8b9f04c415a96c92fc36b7639cd1877903f3f0eb"
NEWM_REV = "d120fcc390eba70593aecfafbafefe8647fd5c92"
GLUEWC_REV = "0e602ca06e35e6d4f535a077dd89b15c4fdc6f89"
GLUEQS_REV = "1c787c3fa8ade2d7fe1148c5f76facdb8313053e"
SCENEFX_REV = "37ccd723bef49e6891156ffafce8f549f01446cc"

cfgsessions = {
    "minimal": {"console": True},
    "labwc": {"compositor": "labwc", "opts": ["programs.labwc.enable"]},
    "labwc-noctalia": {
        "compositor": "labwc",
        "shell": "noctalia",
        "opts": ["programs.labwc.enable"],
    },
    "lxqt": {
        "compositor": "labwc",
        "opts": ["programs.lxqt.enable", "programs.labwc.enable"],
    },
    "plasma": {
        "compositor": "plasma",
        "opts": ["programs.plasma.enable"],
        "elogind": True,
    },
    "sway": {"compositor": "sway", "opts": ["programs.sway.enable"]},
    "sway-noctalia": {
        "compositor": "sway",
        "shell": "noctalia",
        "opts": ["programs.sway.enable"],
    },
    "niri": {"compositor": "niri", "opts": ["programs.niri.enable"]},
    "niri-noctalia": {
        "compositor": "niri",
        "shell": "noctalia",
        "opts": ["programs.niri.enable", "programs.xwayland-satellite.enable"],
    },
    "vxwm": {
        "compositor": "vxwm",
        "opts": ["programs.xorg.enable", "programs.xinit.enable"],
    },
    "newm": {"compositor": "newm"},
    "mango": {"compositor": "mango", "opts": ["programs.mango.enable"]},
    "mango-noctalia": {
        "compositor": "mango",
        "shell": "noctalia",
        "opts": ["programs.mango.enable"],
    },
    "nvwm": {
        "compositor": "nvwm",
        "opts": ["programs.xorg.enable", "programs.xinit.enable"],
    },
    "gluewc": {"compositor": "gluewc"},
    "gluewc-glueqs": {"compositor": "gluewc", "shell": "glueqs"},
}
cfgsessiondefault = "labwc"
COMPOSITORS = ("labwc", "sway", "niri", "mango", "plasma", "nvwm", "vxwm", "newm", "gluewc")

cfgbootefi = """  # bootloader
  programs.limine.enable = true;
  programs.limine.efiSupport = true;
  programs.limine.settings.editor_enabled = true;
  programs.limine.settings.wallpaper = [ ];
  boot.loader.efi.canTouchEfiVariables = true;

"""

cfgbootbios = """  # bootloader
  programs.limine.enable = true;
  programs.limine.biosSupport = true;
  programs.limine.biosDevice = "@@bootdev@@";
  programs.limine.settings.wallpaper = [ ];

"""

cfgbootnone = """  programs.limine.enable = false;

"""

cfgemergency = """  # root shell on the console when stage 1 fails
  boot.initrd.emergencyAccess = true;

"""

cfgtime = """  time.timeZone = "@@timezone@@";
"""

cfglocale = """  i18n.defaultLocale = "@@LANG@@";
"""

cfglocaleextra = """  i18n.extraLocaleSettings = {
    LC_ADDRESS = "@@LC_ADDRESS@@";
    LC_IDENTIFICATION = "@@LC_IDENTIFICATION@@";
    LC_MEASUREMENT = "@@LC_MEASUREMENT@@";
    LC_MONETARY = "@@LC_MONETARY@@";
    LC_NAME = "@@LC_NAME@@";
    LC_NUMERIC = "@@LC_NUMERIC@@";
    LC_PAPER = "@@LC_PAPER@@";
    LC_TELEPHONE = "@@LC_TELEPHONE@@";
    LC_TIME = "@@LC_TIME@@";
  };
"""

cfgconsole = """  hardware.console.keyMap = "@@vconsole@@";

"""

cfgusers = """  users.users."@@username@@" = {
    isNormalUser = true;
    description = "@@fullname@@";
    extraGroups = [ @@groups@@ ];
  };

"""

cfgpkgs = """  environment.systemPackages = with pkgs; [
    vim
    git
    wget
    iproute2
    iputils
    pciutils
    shadow
@@guipkgs@@    (lib.hiPrio (writeShellScriptBin "@@rebuildcmd@@" ''
      set -e
      ${git}/bin/git -C @@etcdir@@ add -A
      exec ${nixos-rebuild}/bin/nixos-rebuild "''${1:-switch}" --flake @@etcdir@@#finixos "''${@:2}"
    ''))
    fastfetch
    (writeShellScriptBin "neofetch" ''
      exec env distro="finix $(uname -m)" ${hyfetch}/bin/neowofetch --ascii_distro nixos --ascii_colors 1 8 1 8 1 8 "$@"
    '')
  ];

  environment.etc."xdg/fastfetch/config.jsonc".text = builtins.toJSON {
    logo = {
      source = "nixos";
      color = {
        "1" = "31";
        "2" = "90";
        "3" = "31";
        "4" = "90";
        "5" = "31";
        "6" = "90";
      };
    };
    modules = [
      "title" "separator" "os" "host" "kernel" "uptime" "packages" "shell"
      "display" "de" "wm" "wmtheme" "theme" "icons" "font" "cursor"
      "terminal" "terminalfont" "cpu" "gpu" "memory" "swap" "disk"
      "localip" "battery" "poweradapter" "locale" "break" "colors"
    ];
  };

"""

cfgguipkgs = """    foot
    firefox
"""

cfgtail = """  # services.openssh.enable = true;
}
"""

cfglatestkernel = """  boot.kernelPackages = pkgs.linuxPackages_latest;

"""

cfgflaketemplate = """{
  description = "finix system";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/@@nixpkgs_rev@@";
    finix.url = "github:finix-community/finix/@@finix_rev@@";
@@extra_inputs@@  };

  outputs = inputs @ { self, nixpkgs, finix, ... }: let
    pkgs = import nixpkgs {
      system = "x86_64-linux";
      config.allowUnfree = true;
    };
  in {
    nixosConfigurations.finixos = finix.lib.finixSystem {
      inherit (pkgs) lib;

      modules = with finix.nixosModules; [
        { nixpkgs.pkgs = nixpkgs.lib.mkDefault pkgs; }
        ./configuration.nix
        ./sessions.nix
        ./branding.nix
@@modules@@      ];

      specialArgs = {
        modulesPath = toString nixpkgs + "/nixos/modules";
        inherit inputs;
      };
    } // {
      meta.position = "@@etcdir@@/configuration.nix:1";
    };
  };
}
"""

BASE_MODULES = [
    "nix-daemon", "chronyd", "bluetooth", "openssh", "sysklogd", "limine",
    "sudo", "polkit", "getty", "bash", "dhcpcd", "iwd",
]


def parse_desktop_selection(raw_choice, warn=None):
    if warn is None:
        warn = lambda msg: None
    selected = []
    for choice in raw_choice.split(","):
        choice = choice.strip()
        if not choice:
            continue
        if choice not in cfgsessions:
            warn("Unknown desktop choice '{}', skipping".format(choice))
            continue
        if choice not in selected:
            selected.append(choice)
    if not selected:
        warn("No (valid) desktop selected, falling back to {}".format(cfgsessiondefault))
        selected = [cfgsessiondefault]

    entries = [cfgsessions[s] for s in selected]
    comps = [e["compositor"] for e in entries if e.get("compositor")]
    needs = {
        "console_only": all(e.get("console") for e in entries),
        "elogind": any(e.get("elogind") for e in entries),
    }
    needs["audio"] = not needs["console_only"]
    for c in COMPOSITORS:
        needs[c] = c in comps
    needs["noctalia"] = []
    needs["plain"] = []
    for e in entries:
        comp = e.get("compositor")
        if not comp:
            continue
        if e.get("shell") == "noctalia" and comp not in needs["noctalia"]:
            needs["noctalia"].append(comp)
        if not e.get("shell") and comp not in needs["plain"]:
            needs["plain"].append(comp)
    needs["glueqs"] = any(e.get("shell") == "glueqs" for e in entries)
    needs["opts"] = []
    for e in entries:
        for opt in e.get("opts", []):
            if opt not in needs["opts"]:
                needs["opts"].append(opt)
    return selected, needs


def flake_modules(needs):
    mods = list(BASE_MODULES)
    if not needs["console_only"]:
        mods.append("regreet")
    if needs["audio"]:
        mods += ["pipewire", "wireplumber", "rtkit"]
    for opt in needs["opts"]:
        name = opt.split(".")[1]
        if name != "plasma" and name not in mods:
            mods.append(name)
    if needs["plasma"]:
        mods.append("upower")
    if needs["elogind"] and "xorg" not in mods:
        mods.append("xorg")
    return mods


def build_flake(needs, etcdir="/etc/finix"):
    def src(name, url):
        return (
            "    " + name + " = {\n"
            '      url = "' + url + '";\n'
            "      flake = false;\n"
            "    };\n"
        )

    extra_inputs = ""
    if needs["noctalia"]:
        extra_inputs += src("noctalia-src", "github:noctalia-dev/noctalia-shell/" + NOCTALIA_REV)
    if needs["nvwm"]:
        extra_inputs += src("nvwm-src", "github:Vifuddyxg/nvwm/" + NVWM_REV)
    if needs["vxwm"]:
        extra_inputs += src("vxwm-src", "git+https://codeberg.org/wh1tepearl/vxwm?rev=" + VXWM_REV)
    if needs["gluewc"]:
        extra_inputs += src("gluewc-src", "github:vladbiber/gluewc/" + GLUEWC_REV)
        extra_inputs += src("scenefx-src", "github:wlrfx/scenefx/" + SCENEFX_REV)
    if needs["glueqs"]:
        extra_inputs += src("glueqs-src", "github:vladbiber/glueqs/" + GLUEQS_REV)
    if needs["newm"]:
        extra_inputs += '    newm-flake.url = "github:jbuchermn/newm/' + NEWM_REV + '";\n'

    modules = ""
    if needs["plasma"]:
        modules += "        ./plasma.nix\n"
    modules += "".join("        " + m + "\n" for m in flake_modules(needs))

    flake = cfgflaketemplate
    flake = flake.replace("@@nixpkgs_rev@@", NIXPKGS_REV)
    flake = flake.replace("@@finix_rev@@", FINIX_REV)
    flake = flake.replace("@@extra_inputs@@", extra_inputs)
    flake = flake.replace("@@modules@@", modules)
    flake = flake.replace("@@etcdir@@", etcdir)
    return flake


def detect_cpu_vendor():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("vendor_id"):
                    vendor = line.split(":", 1)[1].strip()
                    if vendor == "GenuineIntel":
                        return "intel"
                    if vendor == "AuthenticAMD":
                        return "amd"
                    return None
    except OSError:
        pass
    return None


def detect_gpu_vendors():
    vendors = set()
    base = "/sys/bus/pci/devices"
    try:
        entries = os.listdir(base)
    except OSError:
        return vendors
    for dev in entries:
        try:
            with open(os.path.join(base, dev, "class")) as f:
                if not f.read().startswith("0x03"):
                    continue
            with open(os.path.join(base, dev, "vendor")) as f:
                vendors.add(f.read().strip())
        except OSError:
            continue
    return vendors


def build_hardware_drivers(cpu_vendor, gpu_vendors, allow_unfree):
    out = "  # hardware\n"
    if cpu_vendor == "intel":
        out += "  hardware.cpu.intel.updateMicrocode = true;\n"
    elif cpu_vendor == "amd":
        out += "  hardware.cpu.amd.updateMicrocode = true;\n"

    if "0x10de" in gpu_vendors:
        out += "  # nvidia: nouveau by default\n"
        if not allow_unfree:
            out += "  # (the proprietary driver also needs allowUnfree in flake.nix)\n"
        out += "  # hardware.nvidia.enable = true;\n"
    if "0x8086" in gpu_vendors:
        out += (
            "  hardware.graphics.extraPackages = with pkgs; [\n"
            "    intel-media-driver\n"
            "    intel-vaapi-driver\n"
            "  ];\n"
        )

    kms = []
    if "0x8086" in gpu_vendors:
        kms.append("i915")
    if "0x1002" in gpu_vendors:
        kms.append("amdgpu")
    if "0x10de" in gpu_vendors:
        kms.append("nouveau")
    if kms:
        out += (
            "  boot.initrd.kernelModules = [ "
            + " ".join('"%s"' % m for m in kms)
            + " ];\n"
        )
    return out + "\n"


BRANDING_NIX = """# limine boot menu group named finix instead of NixOS
{
  config,
  pkgs,
  lib,
  inputs,
  ...
}:
let
  cfg = config.programs.limine;

  limineInstallConfig = pkgs.writeText "limine-install.json" (
    builtins.toJSON {
      inherit (cfg)
        additionalFiles
        biosDevice
        biosSupport
        efiSupport
        enrollConfig
        extraEntries
        force
        partitionIndex
        settings
        validateChecksums
        secureBoot
        ;

      nixPath = config.services.nix-daemon.package;
      efiBootMgrPath = pkgs.efibootmgr;
      liminePath = cfg.package;
      efiMountPoint = config.boot.loader.efi.efiSysMountPoint;
      fileSystems = config.fileSystems;
      canTouchEfiVariables = config.boot.loader.efi.canTouchEfiVariables;
      efiRemovable = cfg.efiInstallAsRemovable;
      maxGenerations = if cfg.maxGenerations == null then 0 else cfg.maxGenerations;
      hostArchitecture = pkgs.stdenv.hostPlatform.parsed.cpu;
      fwupdEfiPath = config.services.fwupd.package or null;
    }
  );

  patchedInstallScript =
    pkgs.runCommand "limine-install-finix.py" { } ''
      sed -e "s|/+NixOS {group_name}|/+finix {group_name}|" \\
        ${inputs.finix}/modules/programs/limine/limine-install.py > $out
    '';
in
{
  config = lib.mkIf (config.providers.bootloader.backend or null == "limine") {
    providers.bootloader.installHook = lib.mkForce (
      pkgs.replaceVarsWith {
        src = patchedInstallScript;
        isExecutable = true;
        replacements = {
          python3 = pkgs.python3.withPackages (python-packages: [ python-packages.psutil ]);
          configPath = limineInstallConfig;
        };
      }
    );
  };
}
"""


PLASMA_NIX = """# KDE Plasma 6 on finix (from the finix modules/plasma branch)
{
  config,
  pkgs,
  lib,
  ...
}:
let
  cfg = config.programs.plasma;

  inherit (pkgs) kdePackages;

  sessionScript = pkgs.writeShellScript "plasma-session" ''
    ${config.programs.pipewire.package}/bin/pipewire &
    ${config.programs.wireplumber.package}/bin/wireplumber &
    ${config.programs.pipewire.package}/bin/pipewire-pulse &
    ${kdePackages.kservice}/bin/kbuildsycoca6 || true
    exec ${kdePackages.plasma-workspace}/bin/startplasma-wayland \\
      >"$HOME/plasma.log" 2>&1
  '';

  sessionFile = pkgs.writeTextDir "share/wayland-sessions/plasma.desktop" ''
    [Desktop Entry]
    Name=Plasma (Wayland)
    Comment=KDE Plasma Desktop
    Exec=${pkgs.dbus}/bin/dbus-run-session -- ${sessionScript}
    Type=Application
    DesktopNames=KDE
  '';

  lnfMetadata = pkgs.writeTextDir "share/plasma/look-and-feel/org.finix.desktop/metadata.json" (
    builtins.toJSON {
      KPackageStructure = "Plasma/LookAndFeel";
      KPlugin = {
        Id = "org.finix.desktop";
        Name = "finix";
        Description = "Breeze Dark with the finix wallpaper";
      };
      "X-Plasma-APIVersion" = "2";
    }
  );
  lnfDefaults = pkgs.writeTextDir "share/plasma/look-and-feel/org.finix.desktop/contents/defaults" ''
    [kdeglobals][KDE]
    widgetStyle=Breeze
    [kdeglobals][General]
    ColorScheme=BreezeDark
    [kdeglobals][Icons]
    Theme=breeze-dark
    [plasmarc][Theme]
    name=default
    [Wallpaper]
    Image=@@wallpaper@@
  '';
in
{
  options.programs.plasma = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Whether to enable the KDE Plasma 6 Wayland session.";
    };
  };

  config = lib.mkIf cfg.enable {
    # kwin needs /tmp/.X11-unix to exist before it starts xwayland
    finit.tmpfiles.rules = [
      "D! /tmp/.X11-unix  1777 root root"
      "z  /tmp/.X11-unix"
    ];

    services.upower.enable = true;

    environment.systemPackages = with kdePackages; [
      (lib.hiPrio sessionFile)

      qtwayland
      qtsvg
      qtimageformats

      kwin
      pkgs.xwayland

      plasma-workspace
      plasma-desktop
      kscreen
      libkscreen
      kscreenlocker
      kactivitymanagerd
      kglobalacceld
      kwrited
      baloo
      milou
      kmenuedit
      kinfocenter
      plasma-systemmonitor
      ksystemstats
      libksysguard
      systemsettings
      kcmutils
      kdeplasma-addons
      pkgs.xdg-user-dirs

      frameworkintegration
      kauth
      kcoreaddons
      kded
      kfilemetadata
      kguiaddons
      kiconthemes
      kimageformats
      kio
      kio-admin
      kio-extras
      kio-fuse
      knighttime
      kpackage
      kservice
      kunifiedpush
      solid
      plasma-activities
      phonon-vlc

      libplasma
      qqc2-desktop-style
      kde-cli-tools

      breeze
      breeze-icons
      breeze-gtk
      kde-gtk-config
      ocean-sound-theme
      pkgs.hicolor-icon-theme
      qqc2-breeze-style
      lnfMetadata
      lnfDefaults

      polkit-kde-agent-1
      plasma-integration
      drkonqi

      plasma-pa
      powerdevil
      pkgs.iwgtk

      kwallet
      kwalletmanager

      dolphin
      konsole
      kate
      ark
      gwenview
      okular
      spectacle
      kdegraphics-thumbnailers
    ];

    environment.pathsToLink = [
      "/share"
      "/libexec"
    ];

    security.pam.environment =
      let
        qtVersions = with pkgs; [
          qt5
          qt6
        ];
      in
      {
        QT_PLUGIN_PATH.default = map (qt: "/run/current-system/sw/${qt.qtbase.qtPluginPrefix}") qtVersions;
        QML2_IMPORT_PATH.default = map (qt: "/run/current-system/sw/${qt.qtbase.qtQmlPrefix}") qtVersions;

        XDG_CONFIG_DIRS.default = [
          "@{HOME}/.config/kdedefaults"
          "/etc/xdg"
        ];

        KPACKAGE_DEP_RESOLVERS_PATH.default = [
          "${kdePackages.frameworkintegration.out}/libexec/kf6/kpackagehandlers"
        ];
      };

    environment.etc."xdg/kdeglobals".text = ''
      [KDE]
      LookAndFeelPackage=org.finix.desktop
    '';

    security.pam.services.kde.text = ''
      auth      substack      login
      account   include       login
      password  substack      login
      session   include       login
    '';

    security.wrappers = {
      kwin_wayland = {
        owner = "root";
        group = "root";
        capabilities = "cap_sys_nice+ep";
        source = "${lib.getBin pkgs.kdePackages.kwin}/bin/kwin_wayland";
      };
    };

    xdg.portal.portals = [
      pkgs.kdePackages.xdg-desktop-portal-kde
      pkgs.xdg-desktop-portal-gtk
    ];
  };
}
"""


_COMPOSITORS = {
    "labwc": {
        "name": "Labwc",
        "cmd": "${config.programs.labwc.package}/bin/labwc",
        "desktop_names": "labwc;wlroots",
        "comment": "labwc stacking compositor",
    },
    "sway": {
        "name": "Sway",
        "cmd": "${config.programs.sway.package}/bin/sway",
        "desktop_names": "sway;wlroots",
        "comment": "Sway i3-compatible compositor",
    },
    "niri": {
        "name": "Niri",
        "cmd": "${config.programs.niri.package}/bin/niri --session",
        "desktop_names": "niri",
        "comment": "Niri scrollable-tiling compositor",
    },
    "mango": {
        "name": "Mango",
        "cmd": "${config.programs.mango.package}/bin/mango",
        "desktop_names": "mango;wlroots",
        "comment": "Mango tiling compositor",
    },
    "gluewc": {
        "name": "gluewc",
        "cmd": "${gluewc}/bin/gluewc-session",
        "desktop_names": "gluewc",
        "comment": "Animated BSP Wayland compositor",
    },
}

# waits for the compositor's wayland socket, then exports WAYLAND_DISPLAY
_WAIT_SOCKET = (
    '    sock=""\n'
    '    i=0\n'
    '    while [ $i -lt 100 ]; do\n'
    '      for s in "$XDG_RUNTIME_DIR"/wayland-*; do\n'
    '        case "$s" in\n'
    '          *.lock) ;;\n'
    '          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;\n'
    '        esac\n'
    '      done\n'
    '      [ -n "$sock" ] && break\n'
    '      i=$((i + 1))\n'
    '      sleep 0.1\n'
    '    done\n'
    '    if [ -n "$sock" ]; then\n'
    '      export WAYLAND_DISPLAY="$sock"\n'
    '      export DISPLAY=:0\n'
)


def _desktop_entry(fname, name, comment, exec_, desktop_names, prio=None):
    open_ = "    (lib.setPrio (%d) (" % prio if prio is not None else "    ("
    close = "))\n" if prio is not None else ")\n"
    return (
        open_ + 'pkgs.writeTextDir "share/wayland-sessions/' + fname + '" \'\'\n'
        '      [Desktop Entry]\n'
        '      Name=' + name + '\n'
        '      Comment=' + comment + '\n'
        '      Exec=' + exec_ + '\n'
        '      Type=Application\n'
        '      DesktopNames=' + desktop_names + '\n'
        '    \'\'' + close
    )


def _noctalia_session_nix(comp, wallpaper, replaces_plain=False):
    c = _COMPOSITORS[comp]
    args = " -c /etc/sway/config-noctalia" if comp == "sway" else ""
    niri_socket = ""
    if comp == "niri":
        niri_socket = (
            '      i=0\n'
            '      while [ $i -lt 20 ]; do\n'
            '        for ns in "$XDG_RUNTIME_DIR"/niri.*.sock; do\n'
            '          if [ -S "$ns" ]; then export NIRI_SOCKET="$ns"; break 2; fi\n'
            '        done\n'
            '        i=$((i + 1))\n'
            '        sleep 0.1\n'
            '      done\n'
        )
    script = (
        '  session-' + comp + '-noctalia = pkgs.writeShellScript "session-' + comp + '-noctalia" \'\'\n'
        '    ' + c["cmd"] + args + ' >"$XDG_RUNTIME_DIR/' + comp + '-compositor.log" 2>&1 &\n'
        '    comp=$!\n'
        + _WAIT_SOCKET
        + niri_socket +
        '      ${pkgs.swaybg}/bin/swaybg -i ' + wallpaper + ' -m fill &\n'
        '      ${audioStart}\n'
        '      (\n'
        '        ${noctalia}/bin/noctalia --daemon >"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &\n'
        '        np=$!\n'
        '        sleep 5\n'
        '        if ! kill -0 "$np" 2>/dev/null; then\n'
        '          echo "noctalia exited early; retrying with software rendering" \\\n'
        '            >>"$XDG_RUNTIME_DIR/noctalia.log"\n'
        '          QT_QUICK_BACKEND=software LIBGL_ALWAYS_SOFTWARE=1 \\\n'
        '            ${noctalia}/bin/noctalia --daemon \\\n'
        '            >>"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &\n'
        '        fi\n'
        '      ) &\n'
        '    fi\n'
        '    wait "$comp"\n'
        '  \'\';\n'
    )
    desktop = _desktop_entry(
        (comp if replaces_plain else comp + "-noctalia") + ".desktop",
        c["name"] + " + Noctalia",
        c["comment"] + " with the Noctalia desktop shell",
        "${pkgs.dbus}/bin/dbus-run-session -- ${session-" + comp + "-noctalia}",
        c["desktop_names"],
        prio=-20 if replaces_plain else None,
    )
    return script, desktop


def _plain_audio_session_nix(comp):
    c = _COMPOSITORS[comp]
    script = (
        '  session-' + comp + ' = pkgs.writeShellScript "session-' + comp + '" \'\'\n'
        '    ${audioStart}\n'
        '    exec ' + c["cmd"] + '\n'
        '  \'\';\n'
    )
    desktop = _desktop_entry(
        comp + ".desktop",
        c["name"],
        c["comment"],
        "${pkgs.dbus}/bin/dbus-run-session -- ${session-" + comp + "}",
        c["desktop_names"],
        prio=-10,
    )
    return script, desktop


_GLUEWC_NIX_LET = """  gluewcUdev =
    if config.services.mdevd.enable || config.services.keventd.enable then
      pkgs.libudev-zero
    else
      null;
  gluewcLibinput = pkgs.libinput.override (
    lib.optionalAttrs (gluewcUdev != null) {
      udev = gluewcUdev;
      wacomSupport = false;
    }
  );
  gluewcWlroots = pkgs.wlroots_0_20.override { libinput = gluewcLibinput; };
  scenefx = pkgs.stdenv.mkDerivation {
    pname = "scenefx";
    version = "0.5.0";
    src = inputs.scenefx-src;
    strictDeps = true;
    depsBuildBuild = [ pkgs.pkg-config ];
    nativeBuildInputs = with pkgs; [
      meson
      ninja
      pkg-config
      scdoc
      wayland-scanner
    ];
    buildInputs = with pkgs; [
      gluewcWlroots
      wayland
      wayland-protocols
      libdrm
      libxkbcommon
      pixman
      libGL
      libgbm
      libxcb
      libxcb-wm
      lcms2
    ];
    mesonFlags = [ "-Dexamples=false" "-Dwerror=false" ];
  };
  gluewc = pkgs.stdenv.mkDerivation {
    pname = "gluewc";
    version = "0.3.0";
    src = inputs.gluewc-src;
    strictDeps = true;
    nativeBuildInputs = with pkgs; [
      pkg-config
      wayland-scanner
      makeWrapper
    ];
    buildInputs = with pkgs; [
      gluewcWlroots
      gluewcLibinput
      scenefx
      wayland
      wayland-protocols
      libxkbcommon
      pixman
      libdrm
      libGL
      libgbm
      seatd
      libxcb
      libxcb-wm
    ];
    makeFlags = [
      "PREFIX=${placeholder "out"}"
      "SESSIONDIR=${placeholder "out"}/share/wayland-sessions"
      "VERSION=0.3.0"
      "WAYLAND_SCANNER=wayland-scanner"
    ];
    postInstall = ''
      wrapProgram $out/bin/gluewc-session \\
        --set-default GLUEWC_DATADIR $out/share/gluewc \\
        --prefix PATH : ${
          lib.makeBinPath [
            pkgs.dbus
            config.programs.pipewire.package
            config.programs.wireplumber.package
            pkgs.xwayland
            pkgs.procps
          ]
        }:$out/bin
    '';
  };
"""

_GLUEWC_PKGS = """    gluewc
    pkgs.alacritty
    pkgs.rofi
    pkgs.grim
    pkgs.slurp
    pkgs.wl-clipboard
"""

_GLUEQS_NIX_LET = """  glueqsConfig = pkgs.runCommand "glueqs-config" { nativeBuildInputs = [ pkgs.jq ]; } ''
    cp -r ${inputs.glueqs-src} $out
    chmod -R u+w $out
    jq '.wallpaper = "@@wallpaper@@" | .dockUsage = ""' ${inputs.glueqs-src}/settings.json > $out/settings.json
  '';
"""

_GLUEQS_PKGS = """    pkgs.quickshell
    pkgs.curl
    pkgs.bluez
    pkgs.procps
"""

_LOGINCTL_SHIM = """    (pkgs.writeShellScriptBin "loginctl" ''
      case "$1" in
        reboot) exec reboot ;;
        poweroff) exec poweroff ;;
      esac
      exit 1
    '')
"""


def _gluewc_session_nix(wallpaper, with_bar, replaces_plain=False):
    c = _COMPOSITORS["gluewc"]
    suffix = "-glueqs" if with_bar else ""
    if with_bar:
        seed = (
            "    d=\"''${XDG_CONFIG_HOME:-$HOME/.config}/quickshell/glueqs\"\n"
            '    if [ ! -e "$d" ]; then\n'
            '      mkdir -p "$(dirname "$d")"\n'
            '      cp -rL ${glueqsConfig} "$d"\n'
            '      chmod -R u+w "$d"\n'
            '    fi\n'
        )
        shell = '      ${pkgs.quickshell}/bin/qs -c glueqs >"$XDG_RUNTIME_DIR/glueqs.log" 2>&1 &\n'
    else:
        seed = ""
        shell = '      ${pkgs.swaybg}/bin/swaybg -i ' + wallpaper + ' -m fill &\n'
    script = (
        '  session-gluewc' + suffix + ' = pkgs.writeShellScript "session-gluewc' + suffix + '" \'\'\n'
        + seed +
        '    ' + c["cmd"] + ' &\n'
        '    comp=$!\n'
        + _WAIT_SOCKET
        + shell +
        '    fi\n'
        '    wait "$comp"\n'
        '  \'\';\n'
    )
    desktop = _desktop_entry(
        ("gluewc" if replaces_plain or not with_bar else "gluewc-glueqs") + ".desktop",
        c["name"] + (" + glueqs" if with_bar else ""),
        c["comment"] + (" with the glueqs bar" if with_bar else ""),
        "${pkgs.dbus}/bin/dbus-run-session -- ${session-gluewc" + suffix + "}",
        c["desktop_names"],
        prio=-20,
    )
    return script, desktop


_NVWM_NIX_LET = """  nvwm = pkgs.stdenv.mkDerivation {
    pname = "nvwm";
    version = "0-unstable-pinned";
    src = inputs.nvwm-src;
    buildInputs = with pkgs; [
      libx11
      libxinerama
      libxrandr
      libxcomposite
      libxrender
    ];
    makeFlags = [
      "PREFIX=${placeholder "out"}"
      "SYSCONFDIR=${placeholder "out"}/etc"
    ];
  };

  session-nvwm = pkgs.writeShellScript "session-nvwm" ''
    ${pkgs.xwallpaper}/bin/xwallpaper --zoom @@wallpaper@@ &
    ${audioStart}
    exec ${nvwm}/bin/nvwm
  '';
"""

# no "--" in the X11 Exec lines: startx takes it as its own separator
_NVWM_NIX_DESKTOP = """    (pkgs.writeTextDir "share/xsessions/nvwm.desktop" ''
      [Desktop Entry]
      Name=NVWM
      Comment=Vim-inspired tiling X11 window manager
      Exec=${pkgs.dbus}/bin/dbus-run-session ${session-nvwm}
      Type=Application
      DesktopNames=nvwm
    '')
    pkgs.alacritty
    pkgs.rofi
    pkgs.maim
"""

_VXWM_NIX_LET = """  vxwm = pkgs.stdenv.mkDerivation {
    pname = "vxwm";
    version = "2.3-pinned";
    src = inputs.vxwm-src;
    buildInputs = with pkgs; [
      libx11
      libxft
      libxinerama
      fontconfig
      freetype
    ];
    makeFlags = [
      "PREFIX=${placeholder "out"}"
      "X11INC=${pkgs.libx11.dev}/include"
      "X11LIB=${pkgs.libx11}/lib"
      "FREETYPEINC=${pkgs.freetype.dev}/include/freetype2"
    ];
  };

  session-vxwm = pkgs.writeShellScript "session-vxwm" ''
    ${pkgs.xwallpaper}/bin/xwallpaper --zoom @@wallpaper@@ &
    ${audioStart}
    exec ${vxwm}/bin/vxwm
  '';
"""

_VXWM_NIX_DESKTOP = """    vxwm
    (pkgs.writeTextDir "share/xsessions/vxwm.desktop" ''
      [Desktop Entry]
      Name=vxwm
      Comment=Versatile dwm-style X11 tiling window manager
      Exec=${pkgs.dbus}/bin/dbus-run-session ${session-vxwm}
      Type=Application
      DesktopNames=vxwm
    '')
    pkgs.st
    pkgs.dmenu
"""

_NEWM_NIX_LET = """  session-newm = pkgs.writeShellScript "session-newm" ''
    ${audioStart}
    exec ${inputs.newm-flake.packages.x86_64-linux.newm}/bin/start-newm
  '';
"""

_NEWM_NIX_DESKTOP = """    inputs.newm-flake.packages.x86_64-linux.newm
    (pkgs.writeTextDir "share/wayland-sessions/newm.desktop" ''
      [Desktop Entry]
      Name=newm
      Comment=Touchpad-centric Wayland compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-newm}
      Type=Application
      DesktopNames=newm
    '')
    pkgs.alacritty
    pkgs.wob
    pkgs.pulseaudio
"""

_AUDIO_START = """  audioStart = ''
    ${config.programs.pipewire.package}/bin/pipewire &
    ${config.programs.wireplumber.package}/bin/wireplumber &
    ${config.programs.pipewire.package}/bin/pipewire-pulse &
  '';
"""

_SWAY_CONFIG_LET = """  swayConfigBase = "${config.programs.sway.package}/etc/sway/config";
  swayWallpaper = "output * bg @@wallpaper@@ fill";
  swayConfig = pkgs.runCommand "sway-config" { } ''
    cat ${swayConfigBase} > $out
    echo "${swayWallpaper}" >> $out
  '';
  swayConfigNoctalia = pkgs.runCommand "sway-config-noctalia" { } ''
    sed "/^bar {/,$ d" ${swayConfigBase} > $out
    echo "${swayWallpaper}" >> $out
  '';
"""

_SEED_LET = """  seed-user-configs = pkgs.writeShellScript "seed-user-configs" ''
    export PATH=${pkgs.coreutils}/bin:$PATH
    seed() {
      [ -e "$1" ] || return 0
      [ -e "$2" ] && return 0
      mkdir -p "$(dirname "$2")"
      cp -rL "$1" "$2" || return 0
      chmod -R u+w "$2"
    }
    while IFS=: read -r user _ uid gid _ home _; do
      [ "$uid" -ge 1000 ] && [ "$uid" -lt 65000 ] || continue
      [ -d "$home" ] || continue
      h="$home"
@@seeds@@      chown -R "$uid:$gid" "$h/.config" 2>/dev/null || true
    done < /etc/passwd
  '';
"""


def _nix_etc_text(path, body):
    indented = "".join(
        ("      " + line if line.strip() else "") + "\n"
        for line in body.splitlines()
    )
    return (
        '  environment.etc."' + path + '".text = \'\'\n' + indented + "  \'\';\n"
    )


def build_sessions_nix(needs, etcdir="/etc/finix"):
    wallpaper = etcdir + "/wallpaper.png"
    let_parts = []
    pkg_parts = []
    etc_parts = []

    if needs["audio"]:
        let_parts.append(_AUDIO_START)

    if needs["noctalia"]:
        let_parts.append(
            '  noctalia = pkgs.callPackage (inputs.noctalia-src + "/nix/package.nix") { };\n'
        )
        for comp in needs["noctalia"]:
            script, desktop = _noctalia_session_nix(
                comp, wallpaper, replaces_plain=comp not in needs["plain"]
            )
            let_parts.append(script)
            pkg_parts.append(desktop)

    for comp in needs["plain"]:
        if comp in ("labwc", "sway", "niri", "mango"):
            script, desktop = _plain_audio_session_nix(comp)
            let_parts.append(script)
            pkg_parts.append(desktop)

    if needs["gluewc"]:
        let_parts.append(_GLUEWC_NIX_LET)
        pkg_parts.append(_GLUEWC_PKGS)
        if "gluewc" in needs["plain"]:
            script, desktop = _gluewc_session_nix(wallpaper, False)
            let_parts.append(script)
            pkg_parts.append(desktop)
            pkg_parts.append("    pkgs.swaybg\n")
        if needs["glueqs"]:
            let_parts.append(_GLUEQS_NIX_LET.replace("@@wallpaper@@", wallpaper))
            script, desktop = _gluewc_session_nix(
                wallpaper, True, replaces_plain="gluewc" not in needs["plain"]
            )
            let_parts.append(script)
            pkg_parts.append(desktop)
            pkg_parts.append(_GLUEQS_PKGS)
            if not needs["elogind"]:
                pkg_parts.append(_LOGINCTL_SHIM)

    if needs["nvwm"]:
        let_parts.append(_NVWM_NIX_LET.replace("@@wallpaper@@", wallpaper))
        pkg_parts.append(_NVWM_NIX_DESKTOP)
        pkg_parts.append("    nvwm\n")
        etc_parts.append(
            '  environment.etc."nvwm/config.conf".source = "${nvwm}/etc/nvwm/config.conf";\n'
        )

    if needs["mango"]:
        etc_parts.append(
            '  environment.etc."mango/config.conf".source =\n'
            '    config.programs.mango.package.src + "/assets/config.conf";\n'
        )

    if needs["labwc"]:
        etc_parts.append(
            '  environment.etc."xdg/labwc/rc.xml".source =\n'
            '    config.programs.labwc.package.src + "/docs/rc.xml";\n'
            '  environment.etc."xdg/labwc/menu.xml".source =\n'
            '    config.programs.labwc.package.src + "/docs/menu.xml";\n'
        )
        etc_parts.append(
            _nix_etc_text(
                "xdg/labwc/autostart",
                "# copy /etc/xdg/labwc to ~/.config/labwc to customize\n"
                "swaybg -i " + wallpaper + " -m fill >/dev/null 2>&1 &\n",
            )
        )

    if needs["sway"]:
        let_parts.append(_SWAY_CONFIG_LET.replace("@@wallpaper@@", wallpaper))
        etc_parts.append(
            '  environment.etc."sway/config".source = swayConfig;\n'
            '  environment.etc."xdg/sway/config".source = swayConfig;\n'
        )
        if "sway" in needs["noctalia"]:
            etc_parts.append(
                '  environment.etc."sway/config-noctalia".source = swayConfigNoctalia;\n'
            )

    if needs["vxwm"]:
        let_parts.append(_VXWM_NIX_LET.replace("@@wallpaper@@", wallpaper))
        pkg_parts.append(_VXWM_NIX_DESKTOP)

    if needs["newm"]:
        let_parts.append(_NEWM_NIX_LET)
        pkg_parts.append(_NEWM_NIX_DESKTOP)

    if not needs["console_only"]:
        etc_parts.append(
            '  environment.pathsToLink = [ "/share/applications" "/share/xsessions" ];\n'
            '  xdg.icons.enable = true;\n'
        )

    if needs["nvwm"] or needs["vxwm"]:
        etc_parts.append("  security.wrappers.X.enable = lib.mkForce true;\n")

    if needs["niri"]:
        pkg_parts.append("    pkgs.alacritty\n    pkgs.fuzzel\n")

    if needs["labwc"] or needs["sway"] or needs["mango"]:
        pkg_parts.append("    pkgs.rofi\n")

    if needs["labwc"] or needs["sway"] or needs["noctalia"]:
        pkg_parts.append("    pkgs.swaybg\n")

    seed_pairs = []
    if needs["labwc"]:
        seed_pairs.append(("/etc/xdg/labwc", ".config/labwc"))
    if needs["sway"]:
        seed_pairs.append(("/etc/sway/config", ".config/sway/config"))
    if needs["mango"]:
        seed_pairs.append(("/etc/mango/config.conf", ".config/mango/config.conf"))
    if needs["nvwm"]:
        seed_pairs.append(("/etc/nvwm/config.conf", ".config/nvwm/config.conf"))
    if seed_pairs:
        seeds = "".join(
            '      seed "{}" "$h/{}"\n'.format(src, dst) for src, dst in seed_pairs
        )
        let_parts.append(_SEED_LET.replace("@@seeds@@", seeds))
        etc_parts.append(
            "  system.activation.scripts.seed-user-configs = {\n"
            '    deps = [ "users" ];\n'
            "    text = \"${seed-user-configs}\";\n"
            "  };\n"
        )

    if not needs["elogind"] and not needs["console_only"]:
        poweroff_cmd = "${config.finit.package}/bin/initctl poweroff"
        reboot_cmd = "${config.finit.package}/bin/initctl reboot"
        suspend = '${pkgs.writeShellScript "finix-suspend" "echo mem > /sys/power/state"}'
        pkg_parts.append(
            '    (lib.setPrio (-15) (pkgs.writeShellScriptBin "poweroff" \'\'\n'
            '      [ "$(id -u)" = 0 ] && exec ' + poweroff_cmd + "\n"
            "      exec sudo -n " + poweroff_cmd + "\n"
            "    \'\'))\n"
            '    (lib.setPrio (-15) (pkgs.writeShellScriptBin "reboot" \'\'\n'
            '      [ "$(id -u)" = 0 ] && exec ' + reboot_cmd + "\n"
            "      exec sudo -n " + reboot_cmd + "\n"
            "    \'\'))\n"
            '    (pkgs.writeShellScriptBin "zzz" \'\'\n'
            '      [ "$(id -u)" = 0 ] && exec ' + suspend + "\n"
            "      exec sudo -n " + suspend + "\n"
            "    \'\')\n"
        )
        etc_parts.append(
            "  environment.etc.sudoers.text = lib.mkOrder 2000 ''\n"
            "    %wheel ALL=(root) NOPASSWD: " + poweroff_cmd + ", " + reboot_cmd
            + ", " + suspend + "\n"
            "  '';\n"
        )

    if not let_parts and not etc_parts and not pkg_parts:
        return "{ ... }:\n\n{ }\n"
    if not let_parts:
        out = "{ config, pkgs, lib, ... }:\n\n{\n"
        if pkg_parts:
            out += "  environment.systemPackages = [\n" + "".join(pkg_parts) + "  ];\n"
        out += "".join(etc_parts) + "}\n"
        return out

    out = (
        "{\n  config,\n  pkgs,\n  lib,\n  inputs,\n  ...\n}:\nlet\n"
        + "\n".join(let_parts)
        + "in\n{\n"
    )
    if pkg_parts:
        out += "  environment.systemPackages = [\n" + "".join(pkg_parts) + "  ];\n"
    out += "".join(etc_parts)
    out += "}\n"
    return out


def env_is_set(name):
    envValue = os.environ.get(name)
    return not (envValue is None or envValue == "")


def generateProxyStrings():
    proxyEnv = []
    if env_is_set('http_proxy'):
        proxyEnv.append('http_proxy={}'.format(os.environ.get('http_proxy')))
    if env_is_set('https_proxy'):
        proxyEnv.append('https_proxy={}'.format(os.environ.get('https_proxy')))
    if env_is_set('HTTP_PROXY'):
        proxyEnv.append('HTTP_PROXY={}'.format(os.environ.get('HTTP_PROXY')))
    if env_is_set('HTTPS_PROXY'):
        proxyEnv.append('HTTPS_PROXY={}'.format(os.environ.get('HTTPS_PROXY')))

    if len(proxyEnv) > 0:
        proxyEnv.insert(0, "env")

    return proxyEnv


def pretty_name():
    return _("Installing finix.")


status = pretty_name()


def pretty_status_message():
    return status


def catenate(d, key, *values):
    if [v for v in values if v is None]:
        return

    d[key] = "".join(values)


def fix_btrfs_subvolumes(hardware_config, partitions):
    subvol_map = {
        "/home": "home",
        "/nix": "nix",
    }

    root_is_btrfs = False
    for part in partitions:
        if part.get("mountPoint") == "/" and part.get("fs") == "btrfs":
            root_is_btrfs = True
            break

    if not root_is_btrfs:
        return hardware_config

    libcalamares.utils.debug("Fixing btrfs subvolume configuration")

    for mount_point, correct_subvol in subvol_map.items():
        pattern = r'(fileSystems\."{}"[^;]*"subvol=)[^"]*"'.format(re.escape(mount_point))
        replacement = r'\g<1>{}"'.format(correct_subvol)
        hardware_config = re.sub(pattern, replacement, hardware_config, flags=re.DOTALL)

    return hardware_config


_FINIX_HW_KEEP_PREFIXES = (
    "boot.initrd.availableKernelModules",
    "boot.initrd.kernelModules",
    "boot.kernelModules",
    "boot.extraModulePackages",
    "fileSystems.",
    "fileSystems",
    "swapDevices",
)


def _finix_split_top_level(body):
    stmts = []
    buf = []
    depth = 0
    in_comment = False
    for c in body:
        if in_comment:
            buf.append(c)
            if c == "\n":
                in_comment = False
            continue
        if c == "#":
            in_comment = True
            buf.append(c)
            continue
        if c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
        buf.append(c)
        if c == ";" and depth == 0:
            stmts.append("".join(buf))
            buf = []
    tail = "".join(buf)
    return stmts, tail


def _finix_stmt_key(stmt):
    lhs = stmt.split("=", 1)[0]
    lhs = "\n".join(line.split("#", 1)[0] for line in lhs.splitlines())
    return lhs.strip()


def finixify_hardware_config(hardware_config):
    """keep only the options finix defines, add firmware"""
    first_open = hardware_config.find("{")
    if first_open == -1:
        return hardware_config
    depth = 0
    i = first_open
    while i < len(hardware_config):
        ch = hardware_config[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    colon = hardware_config.find(":", i)
    if colon == -1:
        return hardware_config
    header = hardware_config[: colon + 1]

    rest = hardware_config[colon + 1 :]
    body_open = rest.find("{")
    if body_open == -1:
        return hardware_config
    depth = 0
    j = body_open
    while j < len(rest):
        ch = rest[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    body = rest[body_open + 1 : j]

    stmts, _tail = _finix_split_top_level(body)
    kept = []
    for stmt in stmts:
        key = _finix_stmt_key(stmt)
        if any(key == p or key.startswith(p) for p in _FINIX_HW_KEEP_PREFIXES):
            kept.append(stmt)

    new_body = "".join(kept).rstrip()
    return (
        header
        + "\n\n{\n"
        + new_body
        + "\n\n  hardware.firmware = [\n    pkgs.linux-firmware\n    pkgs.sof-firmware\n  ];\n}\n"
    )


_ACT_COPY_PATH = 100
_ACT_COPY_PATHS = 103
_ACT_BUILDS = 104
_RES_PROGRESS = 105


class NixProgress:
    """progress from nix --log-format internal-json"""

    def __init__(self):
        self._builds_done = 0
        self._builds_expected = 0
        self._copies_done = 0
        self._copies_expected = 0
        self._per_act_progress = {}
        self._copy_bytes = {}
        self._activities = {}
        self.fraction = 0.0
        self._floor = 0.0
        self._floor_done = 0
        self.log_messages = []

    def handle(self, line):
        line = line.strip()
        if not line:
            return True
        if not line.startswith("@nix "):
            return False
        try:
            msg = json.loads(line[5:])
        except (json.JSONDecodeError, ValueError):
            return False

        action = msg.get("action")
        if action == "start":
            self._on_start(msg)
        elif action == "stop":
            self._on_stop(msg)
        elif action == "result":
            self._on_result(msg)
        elif action == "msg":
            level = msg.get("level", 0)
            text = msg.get("msg", "")
            if level <= 1 and text:
                self.log_messages.append(text)

        self._update()
        return True

    def _on_start(self, msg):
        act_id = msg["id"]
        act_type = msg.get("type", 0)
        self._activities[act_id] = act_type
        text = msg.get("text", "")
        if text and msg.get("level", 5) <= 3:
            self.log_messages.append(text)

    def _on_stop(self, msg):
        act_id = msg["id"]
        self._activities.pop(act_id, None)
        self._copy_bytes.pop(act_id, None)

    def _on_result(self, msg):
        act_id = msg["id"]
        res_type = msg.get("type", 0)
        fields = msg.get("fields", [])
        act_type = self._activities.get(act_id, 0)

        if res_type != _RES_PROGRESS or len(fields) < 2:
            return
        if act_type == _ACT_BUILDS:
            self._per_act_progress[(act_type, act_id)] = ("builds", fields[0], fields[1])
            self._recompute_counts()
        elif act_type == _ACT_COPY_PATHS:
            self._per_act_progress[(act_type, act_id)] = ("copies", fields[0], fields[1])
            self._recompute_counts()
        elif act_type == _ACT_COPY_PATH:
            self._copy_bytes[act_id] = (fields[0], max(fields[1], 1))

    def _update(self):
        count_total = self._builds_expected + self._copies_expected
        count_done = self._builds_done + self._copies_done
        if count_total <= 0:
            return

        effective_total = max(count_total, 3)
        count_frac = count_done / effective_total

        total_bytes = sum(t for _, t in self._copy_bytes.values())
        done_bytes = sum(d for d, _ in self._copy_bytes.values())
        if total_bytes > 0:
            byte_sub = done_bytes / total_bytes
            step = len(self._copy_bytes) / effective_total
            raw = count_frac + byte_sub * step
        else:
            raw = count_frac
        raw = max(0.0, min(1.0, raw))

        if raw >= self._floor:
            self._floor = raw
            self._floor_done = count_done
        else:
            new_items = count_done - self._floor_done
            remaining = effective_total - self._floor_done
            if remaining > 0 and new_items >= 0:
                raw = self._floor + (new_items / remaining) * (1.0 - self._floor)
            else:
                raw = self._floor
            raw = max(0.0, min(1.0, raw))
            if raw > self._floor:
                self._floor = raw
                self._floor_done = count_done

        self.fraction = raw

    def _recompute_counts(self):
        bd = be = cd = ce = 0
        for kind, done, expected in self._per_act_progress.values():
            if kind == "builds":
                bd += done
                be += expected
            else:
                cd += done
                ce += expected
        self._builds_done = bd
        self._builds_expected = be
        self._copies_done = cd
        self._copies_expected = ce


def run():
    INSTALL_PROGRESS_START = 0.1
    INSTALL_PROGRESS_END = 1.0

    global status
    status = _("Configuring finix")
    libcalamares.job.setprogress(0.01)

    ngc_cfg = configparser.ConfigParser()
    ngc_cfg["Defaults"] = { "Kernel": "lts" }
    ngc_cfg.read("/etc/nixos-generate-config.conf")

    cfg = cfghead
    gs = libcalamares.globalstorage
    variables = dict()

    root_mount_point = gs.value("rootMountPoint")
    naming = (gs.value("packagechooser_naming") or "").strip()
    if naming not in ("finix", "nixos"):
        naming = "finix"
    etcrel = "etc/nixos" if naming == "nixos" else "etc/finix"
    etcdir = "/" + etcrel
    rebuildcmd = "nixos-rebuild" if naming == "nixos" else "finix-rebuild"
    catenate(variables, "etcdir", etcdir)
    catenate(variables, "rebuildcmd", rebuildcmd)
    config = os.path.join(root_mount_point, etcrel, "configuration.nix")
    fw_type = gs.value("firmwareType")
    bootdev = (
        "nodev"
        if gs.value("bootLoader") is None
        else gs.value("bootLoader")["installPath"]
    )

    if fw_type == "efi":
        cfg += cfgbootefi
    elif bootdev != "nodev":
        cfg += cfgbootbios
        catenate(variables, "bootdev", bootdev)
    else:
        cfg += cfgbootnone

    if ngc_cfg["Defaults"]["Kernel"] == "latest":
        cfg += cfglatestkernel

    debug_choice = (gs.value("packagechooser_debug") or "").split(",")
    if "rescue" in [x.strip() for x in debug_choice]:
        cfg += cfgemergency

    boot_is_partition = False
    for part in gs.value("partitions"):
        if part["claimed"] is True and part["fsName"] in ("luks", "luks2"):
            libcalamares.utils.warning(
                "LUKS partition {} detected: encrypted installs are not "
                "supported by the finix installer yet".format(part.get("device"))
            )
        if part["mountPoint"] == "/boot":
            boot_is_partition = True

    if fw_type == "efi" and boot_is_partition:
        try:
            st = os.statvfs(os.path.join(root_mount_point, "boot"))
            boot_free_mib = st.f_bavail * st.f_frsize // (1024 * 1024)
        except OSError as e:
            libcalamares.utils.warning("could not stat target /boot: {}".format(e))
        else:
            if boot_free_mib < 96:
                return (
                    _("EFI partition is too small"),
                    _(
                        "The EFI system partition mounted at /boot has only "
                        "{} MiB free, but finix needs at least ~96 MiB there "
                        "for the kernel and initrd of one system generation "
                        "(1 GiB total is recommended so several generations "
                        "fit). Please go back to partitioning and enlarge "
                        "the EFI partition."
                    ).format(boot_free_mib),
                )
            elif boot_free_mib < 300:
                libcalamares.utils.warning(
                    "target /boot has only {} MiB free; each finix "
                    "generation needs ~55 MiB, so rebuilds may fill it "
                    "quickly (1 GiB recommended)".format(boot_free_mib)
                )

    libcalamares.job.setprogress(0.03)

    selected, needs = parse_desktop_selection(
        gs.value("packagechooser_packagechooser") or "",
        warn=libcalamares.utils.warning,
    )

    build_cores = 0
    try:
        mem_gb = 0
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_gb = int(line.split()[1]) // (1024 * 1024)
                    break
        cpus = os.cpu_count() or 4
        if mem_gb and mem_gb < 20:
            build_cores = max(1, min(cpus, mem_gb // 2))
    except Exception as e:
        libcalamares.utils.debug("could not size build cores: {}".format(e))

    if build_cores:
        cfg += cfgnixlowram
        catenate(variables, "buildcores", str(build_cores))

    cfg += cfgelogind if needs["elogind"] else cfgseatd
    cfg += cfgnet
    catenate(variables, "hostname", gs.value("hostname") or "finix")

    if gs.value("locationRegion") is not None and gs.value("locationZone") is not None:
        cfg += cfgtime
        catenate(
            variables,
            "timezone",
            gs.value("locationRegion"),
            "/",
            gs.value("locationZone"),
        )

    if gs.value("localeConf") is not None:
        localeconf = gs.value("localeConf")
        locale = localeconf.pop("LANG").split("/")[0]
        cfg += cfglocale
        catenate(variables, "LANG", locale)
        if (
            len(set(localeconf.values())) != 1
            or list(set(localeconf.values()))[0] != locale
        ):
            cfg += cfglocaleextra
            for conf in localeconf:
                catenate(variables, conf, localeconf.get(conf).split("/")[0])
    cfg += "\n"

    if not needs["console_only"]:
        cfg += cfggreet
    if needs["audio"]:
        cfg += cfgaudio

    if needs["opts"]:
        cfg += "  # desktop\n"
        for opt in needs["opts"]:
            cfg += "  {} = true;\n".format(opt)
        cfg += "\n"

    if (
        gs.value("keyboardLayout") is not None
        and gs.value("keyboardVariant") is not None
    ):
        if gs.value("keyboardVConsoleKeymap") is not None:
            try:
                subprocess.check_output(
                    ["pkexec", "loadkeys", gs.value("keyboardVConsoleKeymap").strip()],
                    stderr=subprocess.STDOUT,
                )
                cfg += cfgconsole
                catenate(
                    variables, "vconsole", gs.value("keyboardVConsoleKeymap").strip()
                )
            except subprocess.CalledProcessError as e:
                libcalamares.utils.error("loadkeys: {}".format(e.output))
                libcalamares.utils.error(
                    "Setting vconsole keymap to {} will fail, using default".format(
                        gs.value("keyboardVConsoleKeymap").strip()
                    )
                )
        else:
            kbdmodelmap = open(
                "/run/current-system/sw/share/systemd/kbd-model-map", "r"
            )
            kbd = kbdmodelmap.readlines()
            out = []
            for line in kbd:
                if line.startswith("#"):
                    continue
                out.append(line.split())
            find = []
            for row in out:
                if gs.value("keyboardLayout") == row[1]:
                    find.append(row)
            if find != []:
                vconsole = find[0][0]
            else:
                vconsole = ""
            if gs.value("keyboardVariant") is not None:
                variant = gs.value("keyboardVariant")
            else:
                variant = "-"
            for row in find:
                if variant in row[3]:
                    vconsole = row[0]
                    break
            if vconsole != "" and vconsole != "us" and vconsole is not None:
                try:
                    subprocess.check_output(
                        ["pkexec", "loadkeys", vconsole], stderr=subprocess.STDOUT
                    )
                    cfg += cfgconsole
                    catenate(variables, "vconsole", vconsole)
                except subprocess.CalledProcessError as e:
                    libcalamares.utils.error("loadkeys: {}".format(e.output))
                    libcalamares.utils.error("vconsole value: {}".format(vconsole))
                    libcalamares.utils.error(
                        "Setting vconsole keymap to {} will fail, using default".format(
                            gs.value("keyboardVConsoleKeymap")
                        )
                    )

    if gs.value("username") is not None:
        groups = ["wheel", "video"]
        if needs["audio"]:
            groups.append("audio")

        cfg += cfgusers
        catenate(variables, "username", gs.value("username"))
        catenate(variables, "fullname", gs.value("fullname"))
        groups_nix = (" ").join(['"' + s + '"' for s in groups])
        if not needs["elogind"]:
            groups_nix += " config.services.seatd.group"
        catenate(variables, "groups", groups_nix)

    free = not gs.value("nixos_allow_unfree")

    cfg += build_hardware_drivers(detect_cpu_vendor(), detect_gpu_vendors(), not free)

    cfg += cfgpkgs
    catenate(variables, "guipkgs", "" if needs["console_only"] else cfgguipkgs)

    cfg += cfgtail

    for key in variables.keys():
        pattern = "@@{key}@@".format(key=key)
        if pattern not in cfg:
            libcalamares.utils.warning("Variable '{key}' is not used.".format(key=key))

    variable_pattern = re.compile(r"@@\w+@@")
    for match in variable_pattern.finditer(cfg):
        variable_name = cfg[match.start() + 2 : match.end() - 2]
        if variable_name not in variables:
            libcalamares.utils.warning(
                "Variable '{key}' is used but not defined.".format(key=variable_name)
            )

    for key in variables.keys():
        pattern = "@@{key}@@".format(key=key)
        cfg = cfg.replace(pattern, str(variables[key]))

    status = _("Generating finix configuration")
    libcalamares.job.setprogress(0.05)

    try:
        subprocess.check_output(
            ["pkexec", "nixos-generate-config", "--root", root_mount_point],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        if e.output is not None:
            libcalamares.utils.error(e.output.decode("utf8"))
        return (_("nixos-generate-config failed"), _(e.output.decode("utf8")))

    if etcrel != "etc/nixos":
        libcalamares.utils.host_env_process_output(
            ["mkdir", "-p", root_mount_point + "/" + etcrel], None
        )
        libcalamares.utils.host_env_process_output(
            [
                "mv",
                root_mount_point + "/etc/nixos/hardware-configuration.nix",
                root_mount_point + "/" + etcrel + "/hardware-configuration.nix",
            ],
            None,
        )
        libcalamares.utils.host_env_process_output(
            ["rm", "-rf", root_mount_point + "/etc/nixos"], None
        )

    hf = open(root_mount_point + "/" + etcrel + "/hardware-configuration.nix", "r")
    htxt = hf.read()
    hf.close()

    hardware_modified = False

    try:
        htxt_finix = finixify_hardware_config(htxt)
        if htxt_finix != htxt:
            htxt = htxt_finix
            hardware_modified = True
    except Exception as e:
        libcalamares.utils.warning(
            "finixify_hardware_config failed, using raw nixos-generate-config "
            "output: {}".format(e)
        )

    htxt_fixed = fix_btrfs_subvolumes(htxt, gs.value("partitions"))
    if htxt_fixed != htxt:
        htxt = htxt_fixed
        hardware_modified = True

    search = re.search(r"boot\.extraModulePackages = \[ (.*) \];", htxt)

    if search is not None and free:
        expkgs = search.group(1).split(" ")
        for pkg in expkgs:
            p = ".".join(pkg.split(".")[3:])
            isunfree = subprocess.check_output(
                [
                    "nix-instantiate",
                    "--eval",
                    "--strict",
                    "-E",
                    "with import <nixpkgs> {{}}; pkgs.linuxKernel.packageAliases.linux_default.{}.meta.unfree".format(
                        p
                    ),
                    "--json",
                ],
                stderr=subprocess.STDOUT,
            )
            if isunfree == b"true":
                libcalamares.utils.warning(
                    "{} is marked as unfree, removing from hardware-configuration.nix".format(
                        p
                    )
                )
                expkgs.remove(pkg)
        htxt = re.sub(
            r"boot\.extraModulePackages = \[ (.*) \];",
            "boot.extraModulePackages = [ {}];".format(
                "".join(map(lambda x: x + " ", expkgs))
            ),
            htxt,
        )
        hardware_modified = True

    if hardware_modified:
        libcalamares.utils.host_env_process_output(
            [
                "cp",
                "/dev/stdin",
                root_mount_point + "/" + etcrel + "/hardware-configuration.nix",
            ],
            None,
            htxt,
        )

    libcalamares.utils.host_env_process_output(["cp", "/dev/stdin", config], None, cfg)

    flakepath = os.path.join(root_mount_point, etcrel, "flake.nix")
    libcalamares.utils.host_env_process_output(
        ["cp", "/dev/stdin", flakepath], None, build_flake(needs, etcdir)
    )

    sessionspath = os.path.join(root_mount_point, etcrel, "sessions.nix")
    libcalamares.utils.host_env_process_output(
        ["cp", "/dev/stdin", sessionspath], None, build_sessions_nix(needs, etcdir)
    )

    brandingpath = os.path.join(root_mount_point, etcrel, "branding.nix")
    libcalamares.utils.host_env_process_output(
        ["cp", "/dev/stdin", brandingpath], None, BRANDING_NIX
    )

    wallpaper_src = os.path.join(os.path.dirname(__file__), "finixwallpaper.png")
    if os.path.exists(wallpaper_src):
        libcalamares.utils.host_env_process_output(
            [
                "cp",
                wallpaper_src,
                os.path.join(root_mount_point, etcrel, "wallpaper.png"),
            ],
            None,
        )
    else:
        libcalamares.utils.warning("finixwallpaper.png not found next to main.py")

    if needs["plasma"]:
        plasmapath = os.path.join(root_mount_point, etcrel, "plasma.nix")
        libcalamares.utils.host_env_process_output(
            ["cp", "/dev/stdin", plasmapath], None,
            PLASMA_NIX.replace("@@wallpaper@@", etcdir + "/wallpaper.png"),
        )

    # a path flake must be a git repo, or writing flake.lock changes its hash
    nixosDir = os.path.join(root_mount_point, etcrel)
    try:
        subprocess.check_output(["git", "init", "-q", nixosDir], stderr=subprocess.STDOUT)
        subprocess.check_output(["git", "-C", nixosDir, "add", "-A"], stderr=subprocess.STDOUT)
        subprocess.check_output(
            [
                "git", "-C", nixosDir,
                "-c", "user.email=installer@finix.local",
                "-c", "user.name=finix installer",
                "commit", "-q", "-m", "finix generated system configuration",
            ],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(
            "git init of {} failed: {}".format(nixosDir, e.output)
        )

    status = _("Installing finix")
    libcalamares.job.setprogress(INSTALL_PROGRESS_START)

    try:
        subprocess.check_output(
            ["pkexec", "chmod", "755", root_mount_point],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning("Failed to set permissions on {}: {}".format(root_mount_point, e.output))

    for part in gs.value("partitions"):
        if part.get("fs") == "linuxswap" and part.get("device"):
            try:
                subprocess.check_output(
                    ["pkexec", "swapon", part["device"]],
                    stderr=subprocess.STDOUT,
                )
                libcalamares.utils.debug(
                    "enabled swap on {} for the install".format(part["device"])
                )
            except subprocess.CalledProcessError as e:
                libcalamares.utils.debug(
                    "swapon {} skipped: {}".format(part.get("device"), e.output)
                )

    # build scratch on the target disk, not in the live image's RAM
    build_scratch = os.path.join(root_mount_point, "var/tmp/finix-installer-build")
    build_dir_bound = False
    try:
        subprocess.check_output(
            ["pkexec", "mkdir", "-p", build_scratch, "/nix/var/nix/builds"],
            stderr=subprocess.STDOUT,
        )
        subprocess.check_output(
            ["pkexec", "mount", "--bind", build_scratch, "/nix/var/nix/builds"],
            stderr=subprocess.STDOUT,
        )
        build_dir_bound = True
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(
            "could not bind-mount the build dir onto the target disk: {}".format(e.output)
        )

    nixosInstallCmd = [ "pkexec" ]
    proxyEnv = generateProxyStrings()
    if not proxyEnv:
        proxyEnv = ["env"]
    # a host-side TMPDIR would leak into the target chroot
    proxyEnv.append("TMPDIR=/tmp")
    nixosInstallCmd.extend(proxyEnv)
    nixosInstallCmd.extend(
        [
            "nixos-install",
            "--no-root-passwd",
            "--root",
            root_mount_point,
            "--flake",
            os.path.join(root_mount_point, etcrel) + "#finixos",
            "--max-jobs",
            "1",
        ]
    )
    if build_cores:
        nixosInstallCmd.extend(["--cores", str(build_cores)])
    nixosInstallCmd.extend(
        [
            "--option",
            "experimental-features",
            "nix-command flakes",
            "--log-format",
            "internal-json",
            "--option",
            "build-dir",
            "/nix/var/nix/builds",
        ]
    )

    progress = NixProgress()

    try:
        output = ""
        proc = subprocess.Popen(
            nixosInstallCmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        while True:
            line = proc.stdout.readline().decode("utf-8")
            if not line:
                break

            was_json = progress.handle(line)

            if not was_json:
                output += line
            for log_line in progress.log_messages:
                output += log_line + "\n"

            mapped = INSTALL_PROGRESS_START + progress.fraction * (
                INSTALL_PROGRESS_END - INSTALL_PROGRESS_START
            )
            libcalamares.job.setprogress(mapped)

            for log_line in progress.log_messages:
                libcalamares.utils.debug("nixos-install: {}".format(log_line))
            progress.log_messages.clear()

            if not was_json:
                libcalamares.utils.debug("nixos-install: {}".format(line.strip()))

        exit = proc.wait()
        if exit != 0:
            return (_("finix installation failed"), _(output))
    except:
        return (_("finix installation failed"), _("Installation failed to complete"))
    finally:
        if build_dir_bound:
            try:
                subprocess.check_output(
                    ["pkexec", "umount", "/nix/var/nix/builds"],
                    stderr=subprocess.STDOUT,
                )
                subprocess.check_output(
                    ["pkexec", "rm", "-rf", build_scratch],
                    stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError as e:
                libcalamares.utils.warning(
                    "build-dir cleanup failed: {}".format(e.output)
                )

    libcalamares.job.setprogress(INSTALL_PROGRESS_END)
    return None
