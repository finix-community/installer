#!/usr/bin/env python3
# regenerates iso/everything-*/ from the installer, so the ISO prebuilds the
# same packages the installer asks for. run after changing main.py:
#   python3 scripts/render-vendored-sessions.py
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DIR = os.path.join(REPO, "calamares-finix-extensions/src/modules/nixos")

_stub = types.ModuleType("libcalamares")
_utils = types.ModuleType("libcalamares.utils")
_utils.gettext_path = lambda: None
_utils.gettext_languages = lambda: ["en"]
_utils.warning = lambda *a, **k: None
_utils.debug = lambda *a, **k: None
_stub.utils = _utils
sys.modules["libcalamares"] = _stub
sys.modules["libcalamares.utils"] = _utils

sys.path.insert(0, MODULE_DIR)
import main  # noqa: E402

ALL_SESSIONS = [s for s in main.cfgsessions if s != "minimal"]

FLAVORS = {
    "iso/everything-session": ALL_SESSIONS,
    "iso/everything-mdevd-session": [s for s in ALL_SESSIONS if s != "plasma"],
}


def configuration(needs):
    cfg = main.cfghead + main.cfgbootefi + main.cfgnixlowram
    cfg += main.cfgelogind if needs["elogind"] else main.cfgseatd
    cfg += main.cfgnet + main.cfgtime + main.cfglocale + "\n"
    cfg += main.cfggreet + main.cfgaudio
    cfg += "  # desktop\n"
    for opt in needs["opts"]:
        cfg += "  {} = true;\n".format(opt)
    cfg += "\n" + main.cfgusers + main.cfgpkgs + main.cfgtail
    groups = '"wheel" "video" "audio"'
    if not needs["elogind"]:
        groups += " config.services.seatd.group"
    for key, value in {
        "rebuildcmd": "finix-rebuild",
        "etcdir": "/etc/finix",
        "buildcores": "4",
        "hostname": "finix",
        "timezone": "Europe/Bucharest",
        "LANG": "en_US.UTF-8",
        "username": "tester",
        "fullname": "Tester",
        "groups": groups,
        "guipkgs": main.cfgguipkgs,
    }.items():
        cfg = cfg.replace("@@" + key + "@@", value)
    return cfg


def write(path, text):
    with open(os.path.join(REPO, path), "w") as f:
        f.write(text)
    print("wrote " + path)


for reldir, sessions in FLAVORS.items():
    _, needs = main.parse_desktop_selection(",".join(sessions))
    write(reldir + "/configuration.nix", configuration(needs))
    write(reldir + "/sessions.nix", main.build_sessions_nix(needs))
    write(reldir + "/branding.nix", main.BRANDING_NIX)
    if needs["plasma"]:
        write(reldir + "/plasma.nix", main.PLASMA_NIX.replace("@@wallpaper@@", "/etc/finix/wallpaper.png"))
