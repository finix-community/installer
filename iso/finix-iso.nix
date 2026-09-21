# build: nix build .#iso
{ lib, pkgs, finixPrebuiltSessions ? [ ], ... }:

let
  finixGrubTheme =
    pkgs.runCommand "finix-grub2-theme"
      { nativeBuildInputs = [ pkgs.buildPackages.librsvg pkgs.buildPackages.imagemagick ]; }
      ''
        cp -r ${pkgs.nixos-grub2-theme} $out
        chmod -R u+w $out
        rsvg-convert -h 92 ${../assets/branding/finix-logomark.svg} -o mark.png
        # grub only loads RGB/RGBA png
        magick -size 319x100 xc:none mark.png -gravity center -composite PNG32:$out/logo.png
        magick -size 1x1 xc:'#1A1A1A' PNG32:$out/background.png
        sed -i -e 's/#5579C4/#E33949/g' -e 's/#7EBAE4/#4A4A4A/g' $out/theme.txt
      '';

  finixSplash =
    pkgs.runCommand "finix-splash.png"
      { nativeBuildInputs = [ pkgs.buildPackages.librsvg pkgs.buildPackages.imagemagick ]; }
      ''
        rsvg-convert -h 256 ${../assets/branding/finix-logomark.svg} -o mark.png
        magick -size 1024x768 xc:'#1A1A1A' mark.png -gravity center -composite PNG32:$out
      '';
in
{
  # the installer git-inits the generated flake dir
  environment.systemPackages = [ pkgs.git ];

  nixpkgs.overlays = [
    (final: prev: {
      calamares-nixos-extensions = final.callPackage ../calamares-finix-extensions/package.nix { };

      # plain click toggles items on the multi-select desktop page
      calamares = prev.calamares.overrideAttrs (old: {
        postPatch = (old.postPatch or "") + ''
          substituteInPlace src/modules/packagechooser/PackageChooserPage.cpp \
            --replace-fail "QAbstractItemView::ExtendedSelection" "QAbstractItemView::MultiSelection"
        '';
      });
    })
  ];

  # session packages built from source, so the install copies instead of compiling
  isoImage.storeContents = finixPrebuiltSessions;

  image.baseName = lib.mkForce "finix-graphical-install";
  system.nixos.distroName = lib.mkForce "finix";

  isoImage.grubTheme = finixGrubTheme;
  isoImage.splashImage = finixSplash;
  isoImage.efiSplashImage = finixSplash;

  networking.hostName = "finix-live";

  # hv_* modules fail to load on real hardware and drop the live system into emergency mode
  virtualisation.hypervGuest.enable = lib.mkForce false;
}
