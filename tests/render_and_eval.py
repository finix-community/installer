#!/usr/bin/env python3
"""Render gate: evaluate what the installer would write, for every session combo.

Run it after ANY change to the installer's config generation:

    python3 tests/render_and_eval.py

It stubs libcalamares, imports the real
calamares-finix-extensions/src/modules/nixos/main.py, assembles
configuration.nix from the same fragments in the same order as run(), writes a
complete /etc/finix tree per session combination, git-commits it (a flake needs
a git tree) and runs `nix eval` on the system toplevel's drvPath. That is the
cheap equivalent of what `nixos-install --flake` evaluates: it catches
nonexistent options, duplicate attributes and syntax errors in seconds, without
building anything.

Two combos double as the source of the ISO's pre-built session sets and MUST be
copied into the repo whenever generation changes, or the ISO's pre-built store
paths drift from what a fresh install evaluates:

    cp tests/out/everything/{configuration,sessions,branding,plasma,hardware-configuration}.nix \
       iso/everything-session/
    cp tests/out/everything-mdevd/{configuration,sessions,branding,hardware-configuration}.nix \
       iso/everything-mdevd-session/

Then confirm the flake agrees with the gate (same derivation hashes):

    nix eval --raw .#everything-toplevel.drvPath
    nix eval --raw .#everything-mdevd-toplevel.drvPath
"""

import os
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.environ.get("FINIX_GATE_OUT", os.path.join(HERE, "out"))
MAIN = os.path.join(
    REPO, "calamares-finix-extensions", "src", "modules", "nixos", "main.py"
)
HW_SAMPLE = os.path.join(
    REPO, "reference", "finix-target-sample", "hardware-configuration.nix"
)

# ---- stub libcalamares before importing main.py ----
libcal = types.ModuleType("libcalamares")
libcal.globalstorage = None
libcal.job = types.SimpleNamespace(
    setprogress=lambda *a: None,
    configuration={},
)
libcal.utils = types.SimpleNamespace(
    debug=lambda msg: print("[debug]", msg),
    warning=lambda msg: print("[warn ]", msg),
    error=lambda msg: print("[error]", msg),
    host_env_process_output=lambda *a, **k: None,
    target_env_process_output=lambda *a, **k: None,
    gettext_path=lambda: None,
    gettext_languages=lambda: ["en"],
)
sys.modules["libcalamares"] = libcal
sys.modules["gettext"] = sys.modules.get("gettext") or __import__("gettext")

import importlib.util

spec = importlib.util.spec_from_file_location("finix_main", MAIN)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except Exception as e:
    # main.py has module-level code needing gettext dirs etc.; tolerate
    # only if the templates were loaded.
    print("[warn ] import finished with:", e)
assert hasattr(m, "cfghead"), "main.py templates not loaded"

warned = []
def warn(msg):
    warned.append(msg)
    print("[warn ]", msg)

COMBOS = {
    # name -> comma-separated selection (as the packagechooser GS value)
    "everything": "labwc,labwc-noctalia,lxqt,plasma,sway,niri,niri-noctalia,vxwm,newm,mango,mango-noctalia,nvwm",
    "everything-mdevd": "labwc,labwc-noctalia,lxqt,sway,niri,niri-noctalia,vxwm,newm,mango,mango-noctalia,nvwm",
    "labwc": "labwc",
    "labwc-noctalia": "labwc-noctalia",
    "plasma": "plasma",
    "nvwm": "nvwm",
    "vxwm": "vxwm",
    "newm": "newm",
    "mango-noctalia": "mango-noctalia",
    "minimal": "minimal",
}


def assemble(selection):
    """Mirror run()'s configuration.nix assembly for a UEFI machine with a
    user, RO locale, low-RAM cap — the same shape as the real installs."""
    selected, needs = m.parse_desktop_selection(selection, warn)

    variables = {}
    cat = lambda key, *vals: m.catenate(variables, key, *vals)

    cfg = m.cfghead
    cfg += m.cfgbootefi                     # firmwareType == "efi"
    cfg += m.cfgnixlowram                   # low-RAM machine path
    cat("buildcores", "4")
    cfg += m.cfgelogind if needs["elogind"] else m.cfgseatd
    cfg += m.cfgnetfinix
    cfg += m.cfgnetwork
    cat("hostname", "finix")
    cfg += m.cfgtime
    cat("timezone", "UTC")
    cfg += m.cfglocale
    cat("LANG", "en_US.UTF-8")
    if needs["console_only"]:
        cfg += m.cfggreetnone
    elif needs["nvwm"] or needs["vxwm"]:
        cfg += m.cfggreettuix11
    else:
        cfg += m.cfggreettui
    if needs["audio"]:
        cfg += m.cfgaudio
    session_opts = []
    for s in selected:
        cfg += "  # --- {} ---\n".format(m.cfgsessions[s]["comment"])
        for opt in m.cfgsessions[s]["opts"]:
            if opt not in session_opts:
                session_opts.append(opt)
                cfg += "  {} = true;\n".format(opt)
        cfg += "\n"
    cfg += m.cfgusers
    cat("username", "tester")
    cat("fullname", "Tester")
    groups = ["wheel", "video"]
    if needs["audio"]:
        groups.append("audio")
    if needs["nm"]:
        groups.append("networkmanager")
    groups_nix = (" ").join(['"' + s + '"' for s in groups])
    if not needs["elogind"]:
        groups_nix += " config.services.seatd.group"
    cat("groups", groups_nix)
    cfg += m.cfgpkgs
    cat("pkgs", "")
    cfg += m.cfgtail

    # variable check + substitution, as in run()
    for key in variables:
        if "@@{}@@".format(key) not in cfg:
            warn("Variable '{}' is not used.".format(key))
    import re

    for match in re.compile(r"@@\w+@@").finditer(cfg):
        name = match.group(0).strip("@")
        if name not in variables:
            warn("Variable '{}' is used but not defined.".format(name))
    for key in variables:
        cfg = cfg.replace("@@{}@@".format(key), str(variables[key]))
    return cfg, selected, needs


def run_combo(name, selection):
    d = os.path.join(OUT, name)
    subprocess.run(["rm", "-rf", d], check=True)
    os.makedirs(d)

    cfg, selected, needs = assemble(selection)
    with open(os.path.join(d, "configuration.nix"), "w") as f:
        f.write(cfg)
    with open(os.path.join(d, "flake.nix"), "w") as f:
        f.write(m.build_flake(needs))
    with open(os.path.join(d, "sessions.nix"), "w") as f:
        f.write(m.build_sessions_nix(needs))
    with open(os.path.join(d, "branding.nix"), "w") as f:
        f.write(m.BRANDING_NIX)
    if needs["plasma"]:
        with open(os.path.join(d, "plasma.nix"), "w") as f:
            f.write(m.PLASMA_NIX)

    with open(HW_SAMPLE) as f:
        htxt = m.finixify_hardware_config(f.read())
    with open(os.path.join(d, "hardware-configuration.nix"), "w") as f:
        f.write(htxt)

    subprocess.run(["git", "init", "-q", d], check=True)
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", d, "-c", "user.email=gate@finix.local",
         "-c", "user.name=Gate", "commit", "-q", "-m", "gate render"],
        check=True,
    )

    r = subprocess.run(
        ["nix", "eval", "--raw",
         "{}#nixosConfigurations.finixos.config.system.build.toplevel.drvPath".format(d)],
        capture_output=True, text=True,
    )
    ok = r.returncode == 0 and r.stdout.strip().endswith(".drv")
    print("[{}] {} -> {}".format(
        "PASS" if ok else "FAIL", name,
        r.stdout.strip() if ok else r.stderr.strip()[-2000:],
    ))
    return ok


def main():
    os.makedirs(OUT, exist_ok=True)
    results = {}
    for name, sel in COMBOS.items():
        results[name] = run_combo(name, sel)
    print()
    npass = sum(results.values())
    print("{}/{} combos PASS".format(npass, len(results)))
    sys.exit(0 if npass == len(results) else 1)


if __name__ == "__main__":
    main()
