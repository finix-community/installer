#!/usr/bin/env python3
# evaluates the flake the installer generates, one desktop selection at a time:
#   python3 scripts/eval-session-combos.py            # every combo
#   python3 scripts/eval-session-combos.py sway niri  # only these
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

COMBOS = [
    "labwc",
    "sway",
    "niri",
    "mango",
    "labwc-noctalia",
    "sway-noctalia",
    "niri-noctalia",
    "mango-noctalia",
    "nvwm",
    "vxwm",
    "newm",
    "lxqt",
    "plasma",
    "minimal",
    "gluewc",
    "gluewc-glueqs",
    "gluewc,gluewc-glueqs",
    "sway,niri-noctalia,nvwm",
    "mango-noctalia,nvwm",
]

_SESSION_LINE = re.compile(
    r"^  (programs\.(labwc|sway|niri|mango|lxqt|plasma|xorg|xinit|xwayland-satellite)\.enable = true;"
    r"|# desktop)\s*$"
)


def base_config(needs):
    flavor = "everything-session" if needs["elogind"] else "everything-mdevd-session"
    path = os.path.join(REPO, "iso", flavor, "configuration.nix")
    with open(path) as f:
        lines = [ln for ln in f.read().splitlines(True) if not _SESSION_LINE.match(ln)]
    return flavor, "".join(lines)


def write_combo(raw, workdir):
    selected, needs = main.parse_desktop_selection(raw)
    flavor, cfg = base_config(needs)
    src = os.path.join(REPO, "iso", flavor)

    enables = "".join("  {} = true;\n".format(opt) for opt in needs["opts"])
    idx = cfg.rstrip().rfind("\n}")
    cfg = cfg[:idx] + "\n" + enables + cfg[idx:]

    with open(os.path.join(workdir, "configuration.nix"), "w") as f:
        f.write(cfg)
    with open(os.path.join(workdir, "sessions.nix"), "w") as f:
        f.write(main.build_sessions_nix(needs))
    with open(os.path.join(workdir, "flake.nix"), "w") as f:
        f.write(main.build_flake(needs))
    for extra in ("branding.nix", "hardware-configuration.nix"):
        shutil.copyfile(os.path.join(src, extra), os.path.join(workdir, extra))
    if needs["plasma"]:
        with open(os.path.join(workdir, "plasma.nix"), "w") as f:
            f.write(main.PLASMA_NIX)

    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    subprocess.run(["git", "add", "-A"], cwd=workdir, check=True)
    return selected


def main_():
    combos = sys.argv[1:] or COMBOS
    failures = []
    for raw in combos:
        workdir = tempfile.mkdtemp(prefix="finix-combo-")
        try:
            selected = write_combo(raw, workdir)
            print("==> {} ({})".format(raw, "+".join(selected)), flush=True)
            r = subprocess.run(
                [
                    "nix",
                    "eval",
                    "--no-write-lock-file",
                    "{}#nixosConfigurations.finixos.config.system.build.toplevel.drvPath".format(
                        workdir
                    ),
                ],
                capture_output=True,
                text=True,
            )
            if r.returncode != 0:
                failures.append(raw)
                print(r.stderr.strip()[-2000:], flush=True)
            else:
                print("    OK {}".format(r.stdout.strip()), flush=True)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    if failures:
        print("\nFAILED: {}".format(", ".join(failures)))
        return 1
    print("\nall {} combos evaluate".format(len(combos)))
    return 0


if __name__ == "__main__":
    sys.exit(main_())
