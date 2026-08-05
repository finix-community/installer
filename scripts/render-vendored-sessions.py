#!/usr/bin/env python3
"""Regenerate iso/everything-*/sessions.nix from the installer itself.

Those two directories exist so flake.nix can evaluate the exact systems the
installer produces and bake their session packages into the live ISO's store.
When they drift from main.py the ISO ends up prebuilding packages the target
never asks for, and the install recompiles niri/pipewire/noctalia from source
on the user's laptop instead of copying them.

Run after touching build_sessions_nix (or anything it renders):

    python3 scripts/render-vendored-sessions.py
    nix eval .#nixosConfigurations.finix-iso.config.system.build.isoImage.drvPath

main.py imports libcalamares at module scope, so stub it out first.
"""
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

# every selectable desktop except "minimal", which installs no session
ALL_SESSIONS = [s for s in main.cfgsessions if s != "minimal"]

FLAVORS = {
    # elogind + eudev: the flavor KDE Plasma forces
    "iso/everything-session": ALL_SESSIONS,
    # seatd + mdevd: the finix default, so everything but Plasma
    "iso/everything-mdevd-session": [s for s in ALL_SESSIONS if s != "plasma"],
}


def main_():
    for reldir, sessions in FLAVORS.items():
        _, needs = main.parse_desktop_selection(",".join(sessions))
        path = os.path.join(REPO, reldir, "sessions.nix")
        with open(path, "w") as f:
            f.write(main.build_sessions_nix(needs))
        print("wrote {} ({} sessions)".format(path, len(sessions)))
        # plasma.nix drifts from PLASMA_NIX just as silently as sessions.nix
        # did from build_sessions_nix; render it from the same source
        if needs["plasma"]:
            ppath = os.path.join(REPO, reldir, "plasma.nix")
            with open(ppath, "w") as f:
                f.write(main.PLASMA_NIX.replace("@@wallpaper@@", "/etc/finix/wallpaper.png"))
            print("wrote {}".format(ppath))


if __name__ == "__main__":
    main_()
