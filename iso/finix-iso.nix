# Finix live ISO overlay module: branding, the Calamares fork, and the
# pre-built session store contents.
#
# MANUAL BUILD COMMANDS (heavy; not for CI — the cheap gate is
# tests/render_and_eval.py, which only evaluates):
#
#   Build ISO:
#     nix build .#iso
#
#   Boot-test under QEMU/OVMF (UEFI):
#     nix run nixpkgs#qemu_kvm -- \
#       -enable-kvm -m 4096 -cpu host \
#       -bios "$(nix eval --raw nixpkgs#OVMF.fd)/FV/OVMF.fd" \
#       -cdrom result/iso/*.iso
#
# The OVMF expression nix eval --raw nixpkgs#OVMF.fd evaluates to the built
# derivation output containing FV/OVMF.fd (UEFI firmware image).

{ lib, pkgs, finixPrebuiltSessions ? [ ], ... }:

let
  # Finix-branded GRUB theme: upstream nixos-grub2-theme with the NixOS
  # wordmark/colors swapped for the Finix logomark (red #E33949) on a dark
  # background. logo.png keeps the theme's exact 319x100 canvas so theme.txt
  # geometry stays valid.
  finixGrubTheme =
    pkgs.runCommand "finix-grub2-theme"
      { nativeBuildInputs = [ pkgs.buildPackages.librsvg pkgs.buildPackages.imagemagick ]; }
      ''
        cp -r ${pkgs.nixos-grub2-theme} $out
        chmod -R u+w $out
        rsvg-convert -h 92 ${../assets/branding/finix-logomark.svg} -o mark.png
        # PNG32: forces RGBA (color type 6) — GRUB's PNG loader rejects the
        # grayscale/palette formats ImageMagick otherwise optimizes to, and a
        # single bad image makes GRUB drop the whole theme (text-mode menu).
        magick -size 319x100 xc:none mark.png -gravity center -composite PNG32:$out/logo.png
        magick -size 1x1 xc:'#1A1A1A' PNG32:$out/background.png
        # progress bar: NixOS blues -> Finix red + neutral gray
        sed -i -e 's/#5579C4/#E33949/g' -e 's/#7EBAE4/#4A4A4A/g' $out/theme.txt
      '';

  # Dark splash with the Finix mark, used by the isolinux (BIOS) menu
  # background and as the GRUB fallback background image.
  finixSplash =
    pkgs.runCommand "finix-splash.png"
      { nativeBuildInputs = [ pkgs.buildPackages.librsvg pkgs.buildPackages.imagemagick ]; }
      ''
        rsvg-convert -h 256 ${../assets/branding/finix-logomark.svg} -o mark.png
        magick -size 1024x768 xc:'#1A1A1A' mark.png -gravity center -composite PNG32:$out
      '';
in
{
  # Live-ISO boot menu: stock GRUB/isolinux from iso-image.nix, branded "Finix"
  # via system.nixos.distroName below. An all-Limine live ISO was tried
  # (./limine-iso-boot.nix) and works in QEMU/OVMF, but Limine
  # did not boot reliably under Ventoy on the hardware this was tested on
  # ("config file not found", then a black screen even with a self-contained
  # EFI image), while GRUB did. Limine remains the bootloader of the
  # INSTALLED Finix system; re-enable the import to experiment.
  # imports = [ ./limine-iso-boot.nix ];

  # main.py turns the generated /etc/finix into a git repo before
  # `nixos-install --flake` (avoids a NAR hash mismatch on the path flake),
  # so the live installer environment must provide the git binary.
  environment.systemPackages = [ pkgs.git ];

  # Wire the Finix-branded fork of calamares-nixos-extensions into the ISO.
  # installation-cd-graphical-calamares-plasma6.nix consumes the attr
  # `calamares-nixos-extensions` from nixpkgs; this overlay replaces it with
  # our local fork so Calamares shows Finix branding at runtime.
  nixpkgs.overlays = [
    (final: prev: {
      calamares-nixos-extensions = final.callPackage ../calamares-finix-extensions/package.nix { };

      # packagechooser in the *multiple modes uses Qt ExtendedSelection, where
      # a plain click REPLACES the selection and multi-select needs Ctrl+click
      # — invisible UX for beginners. MultiSelection makes every click toggle
      # the item on/off, which is what a "check several desktops" page needs.
      calamares = prev.calamares.overrideAttrs (old: {
        postPatch = (old.postPatch or "") + ''
          substituteInPlace src/modules/packagechooser/PackageChooserPage.cpp \
            --replace-fail "QAbstractItemView::ExtendedSelection" "QAbstractItemView::MultiSelection"
        '';
      });
    })
  ];

  # Pre-built session packages (from-source builds: niri/mango/labwc/hyprland/
  # pipewire overrides, noctalia, nvwm, xorg...) baked into the live store so
  # nixos-install COPIES them instead of compiling — installs stay fast and
  # safe on low-RAM machines. Merged with the module's own storeContents.
  isoImage.storeContents = finixPrebuiltSessions;

  # Rename the output ISO from the nixos-* default to finix-*.
  # image.baseName was renamed from isoImage.isoBaseName in NixOS 25.05;
  # nixpkgs/nixos-unstable uses image.baseName.
  # lib.mkForce is required: the upstream iso-image.nix sets a non-default value
  # (it evaluates the nixos label + platform into the name), so a plain assignment
  # would produce a "conflicting definition" evaluation error.
  image.baseName = lib.mkForce "finix-graphical-install";

  # Rebrand the live ISO's boot menu (GRUB/syslinux entries are built from
  # system.nixos.distroName) and /etc/os-release NAME in the live session.
  # distroId is left as "nixos" on purpose — tooling (nixos-version, calamares
  # os-release checks) keys off the id, and only the display name should change.
  system.nixos.distroName = lib.mkForce "Finix";

  # Finix-branded GRUB theme + splash images (defaults ship NixOS artwork).
  isoImage.grubTheme = finixGrubTheme;
  isoImage.splashImage = finixSplash;
  isoImage.efiSplashImage = finixSplash;

  networking.hostName = "finix-live";
}
