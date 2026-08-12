# Finix installer

A graphical live ISO that installs [Finix](https://github.com/finix-community/finix).

The image boots straight into a graphical installer built on
[Calamares](https://calamares.io/): pick a disk, a user, a keyboard layout and one or
more desktop sessions, and it writes a complete Finix system — `finit` as PID 1, Limine
as the bootloader, and a flake in `/etc/finix` you can keep editing afterwards.

It started as a fork of NixOS's `calamares-nixos-extensions` and was retargeted at
Finix. A render gate (`tests/render_and_eval.py`) evaluates every session combination
against the Finix module set, so the configuration it writes stays within the options
Finix defines.

## Download

A pre-built image is on the Internet Archive:
**[finix-graphical-install](https://archive.org/details/finix-graphical-install)** —
[direct download](https://archive.org/download/finix-graphical-install/finix-graphical-install.iso)
or [torrent](https://archive.org/download/finix-graphical-install/finix-graphical-install_archive.torrent)
(3.6 GB, x86_64 UEFI).

Check it before writing it to a stick:

```sh
sha256sum finix-graphical-install.iso
# 67d603a5d5af94cbdc8d3d9c503640064a53826096dfbd70b6096b3a27aa83ce
```

Or build it yourself — see [Building the ISO](#building-the-iso).

## What you get

- **UEFI install with Limine**, alongside an existing OS if you want: the ESP is never
  reformatted, so other firmware boot entries survive.
- **A flake-based system in `/etc/finix`** (`configuration.nix`, `sessions.nix`,
  `hardware-configuration.nix`, `flake.nix`), plus a `finix-rebuild` helper that stages
  the directory into git — a flake only sees tracked files — and rebuilds.
- **Pinned inputs.** The generated flake pins nixpkgs to the exact revision the ISO was
  built from, so an install reuses the live image's store instead of resolving a moving
  branch — the same inputs that were tested are the ones you get.
- **Pre-built sessions.** The compositors that the Finix modules rebuild from source
  (against `libudev-zero` under mdevd) are embedded in the ISO, so a fresh install copies
  them instead of compiling — which keeps installs feasible on low-RAM machines.
- **Working defaults.** Sessions come with usable keybindings out of the box — a terminal
  on `Super+Enter`, a launcher on `Super+D` — and the programs those bindings call are
  installed. Where a compositor reads a config file, an editable copy lands in
  `~/.config` on first boot, owned by you; the system copies under `/etc` stay as the
  fallback.

## Sessions

Multi-select is supported — pick as many as you like (Ctrl+click or plain click, both
work).

| Session | Type | Notes |
| --- | --- | --- |
| labwc | Wayland | default; also hosts the LXQt Wayland session |
| labwc + Noctalia | Wayland | Noctalia v5 shell (bar, launcher, lock, OSD) |
| LXQt | Wayland / X11 | full desktop environment |
| KDE Plasma 6 | Wayland | experimental on Finix; see the note below |
| Sway | Wayland | |
| Niri | Wayland | scrollable tiling; excellent built-in keybindings |
| Niri + Noctalia | Wayland | with `xwayland-satellite` |
| Mango (MangoWC) | Wayland | dwl-based |
| Mango + Noctalia | Wayland | |
| newm | Wayland | touchpad-centric, pywm-based; Python config |
| nvwm | X11 | vim-inspired modal tiling WM |
| vxwm | X11 | dwm-style; configuration is compiled in |
| minimal | console | no desktop, no greeter — plain `getty` login |

Login is handled by `greetd` + `tuigreet` for every selection, with `--remember` so your
last user and session come back.

Picking **minimal** today still installs from the same graphical image; it just leaves
out the desktop and the greeter, so you get a console login. A separate, smaller
non-graphical installer image for minimal installs is planned for a future release.

### Plasma changes the plumbing

KWin has no seatd backend — its only session backends are logind, ConsoleKit and Noop —
and elogind resolves device access through the udev database, which mdevd does not
provide. So selecting Plasma switches the installed system to **eudev + elogind**;
every other selection keeps the Finix default of **mdevd + seatd**. The installer picks
for you, and the ISO ships pre-built sessions for both variants.

## Building the ISO

If you just want to install Finix, take the [pre-built image](#download) instead.
Building requires Nix with flakes enabled.

```sh
nix build .#iso
# result/iso/finix-graphical-install.iso
```

Write it to a USB stick, or copy it onto a [Ventoy](https://www.ventoy.net/) drive. If
you use Ventoy, verify the copy — a truncated write produces a file of the right size
that fails deep into the boot:

```sh
sha256sum /path/to/stick/finix-graphical-install.iso
sync && udisksctl unmount -b /dev/sdX1
```

The live image boots via GRUB (Limine is the bootloader of the *installed* system).
`iso/limine-iso-boot.nix` keeps a Limine-booted live image around — it works in QEMU, but
did not boot reliably under Ventoy on the hardware it was tried on, so it is not wired
in.

## Repository layout

| Path | What it is |
| --- | --- |
| `flake.nix` | ISO image, plus the pre-built session sets embedded into it |
| `iso/finix-iso.nix` | live image: branding, Calamares overlay, store contents |
| `iso/everything-session/` | generated config for the eudev+elogind variant (vendored) |
| `iso/everything-mdevd-session/` | generated config for the mdevd+seatd variant (vendored) |
| `calamares-finix-extensions/` | the Calamares fork — branding, module configs, and `src/modules/nixos/main.py`, which generates the installed system |
| `tests/render_and_eval.py` | render gate — evaluates every session combination |
| `scripts/vm-boot-test.sh` | boots the ISO headless under QEMU/OVMF and screenshots it |
| `reference/finix-target-sample/` | a sample generated system, used by the gate |

## Working on the installer

Nearly all behaviour lives in `calamares-finix-extensions/src/modules/nixos/main.py`: it
assembles `configuration.nix` from fragments, renders `sessions.nix` (session launchers,
default configs, seeding) and writes the system flake.

After any change to generation, run the gate:

```sh
python3 tests/render_and_eval.py
```

It renders each session combination into a complete `/etc/finix` tree and runs `nix eval`
on the resulting system — catching missing options, duplicate attributes and syntax
errors in seconds, without building anything.

Two of its outputs are vendored into the repo, because the ISO pre-builds the packages
those configurations resolve to. **Copy them whenever generation changes**, or the ISO's
pre-built store paths silently drift from what a fresh install evaluates:

```sh
cp tests/out/everything/{configuration,sessions,branding,plasma,hardware-configuration}.nix \
   iso/everything-session/
cp tests/out/everything-mdevd/{configuration,sessions,branding,hardware-configuration}.nix \
   iso/everything-mdevd-session/

nix eval --raw .#everything-toplevel.drvPath
nix eval --raw .#everything-mdevd-toplevel.drvPath
```

Those two derivation paths must match what the gate printed.

### Testing beyond the gate

Evaluation cannot tell you whether a session actually starts. The failures that matter
tend to appear only on real hardware, at `nixos-install` time or at first login, so
changes to the login path are worth testing with the exact command the greeter runs —
wrapper, arguments and all — rather than the component alone.

## Credits and licensing

This is a fork of
[calamares-nixos-extensions](https://github.com/NixOS/calamares-nixos-extensions)
(now maintained in nixpkgs), MIT-licensed, with assets under CC-BY-4.0 and CC-BY-SA-4.0.
Changes made here for Finix are published under the same terms, and the upstream notice
is preserved in [LICENSE](LICENSE).

The Finix logomark in `assets/branding/` and
`calamares-finix-extensions/src/branding/` is a recolour of the NixOS snowflake
(CC-BY-SA-4.0), and is therefore itself CC-BY-SA-4.0. It is a placeholder: replace it
with original artwork if the project wants a mark of its own.
