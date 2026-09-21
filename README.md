# finix installer

A graphical live ISO that installs [finix](https://github.com/finix-community/finix).

The image boots into a [Calamares](https://calamares.io/) installer: pick a disk, a
user, a keyboard layout and one or more desktop sessions, and it writes a finix system
with finit as PID 1, Limine as the bootloader and a flake in `/etc/finix`.

It is a fork of NixOS's `calamares-nixos-extensions`, retargeted at finix.

## Download

Pre-built image on the Internet Archive:
[finix-graphical-install](https://archive.org/details/finix-graphical-install),
[direct download](https://archive.org/download/finix-graphical-install/finix-graphical-install.iso),
[torrent](https://archive.org/download/finix-graphical-install/finix-graphical-install_archive.torrent)
(3.6 GB, x86_64, UEFI).

```sh
sha256sum finix-graphical-install.iso
# 67d603a5d5af94cbdc8d3d9c503640064a53826096dfbd70b6096b3a27aa83ce
```

## What you get

- UEFI install with Limine. The ESP is never reformatted, so other boot entries survive.
- A flake in `/etc/finix` (`configuration.nix`, `sessions.nix`, `hardware-configuration.nix`,
  `flake.nix`) and a `finix-rebuild` wrapper that stages the directory into git and rebuilds.
- Pinned inputs: the generated flake uses the nixpkgs and finix revisions the ISO was built
  from, so an install reuses the live store.
- Pre-built sessions: the compositors finix rebuilds against `libudev-zero` are embedded
  in the ISO, so installs copy them instead of compiling.
- Only the modules and packages of the selected sessions go into the generated flake.
- Working defaults: each session comes with its upstream config and the programs its
  keybindings call; an editable copy lands in `~/.config` on first boot.

## Sessions

Several can be selected at once; each one gets an entry in the login screen.

| Session | Type | Notes |
| --- | --- | --- |
| labwc | Wayland | default |
| labwc + Noctalia | Wayland | Noctalia shell |
| gluewc | Wayland | BSP, scrolling and drift layouts, overview |
| gluewc + glueqs | Wayland | with the glueqs Quickshell bar |
| LXQt | Wayland | on labwc |
| KDE Plasma 6 | Wayland | not officially supported by finix yet |
| Sway | Wayland | |
| Sway + Noctalia | Wayland | |
| Niri | Wayland | |
| Niri + Noctalia | Wayland | with xwayland-satellite |
| Mango | Wayland | dwl-based |
| Mango + Noctalia | Wayland | |
| newm | Wayland | pywm, Python config |
| nvwm | X11 | modal tiling WM |
| vxwm | X11 | dwm-style |
| minimal | console | no desktop, no greeter |

Login is regreet under cage.

Plasma needs elogind, and elogind needs the udev database, so selecting Plasma switches
the installed system to eudev + elogind. Everything else uses mdevd + seatd.

## Building the ISO

```sh
nix build .#iso
# result/iso/finix-graphical-install.iso
```

Write it to a USB stick or a Ventoy drive and verify the copy with `sha256sum`.

## Layout

| Path | What it is |
| --- | --- |
| `flake.nix` | the ISO and the pre-built session sets |
| `iso/finix-iso.nix` | live image: branding, Calamares overlay, store contents |
| `iso/everything-session/`, `iso/everything-mdevd-session/` | generated configs with every session, vendored for the ISO build |
| `calamares-finix-extensions/` | the Calamares fork; `src/modules/nixos/main.py` generates the installed system |
| `scripts/render-vendored-sessions.py` | regenerates `iso/everything-*` from `main.py` |
| `scripts/eval-session-combos.py` | evaluates the generated flake for every session combination |

After changing `main.py`:

```sh
python3 scripts/render-vendored-sessions.py
python3 scripts/eval-session-combos.py
```

## License

Fork of [calamares-nixos-extensions](https://github.com/NixOS/calamares-nixos-extensions),
MIT, with assets under CC-BY-4.0 and CC-BY-SA-4.0. See [LICENSE](LICENSE).

The finix logomark is a recolour of the NixOS snowflake (CC-BY-SA-4.0).
