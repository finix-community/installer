# Boot the live ISO itself with Limine instead of NixOS's GRUB/isolinux.
#
# nixpkgs' iso-image.nix hardwires GRUB (UEFI) + isolinux (BIOS) in internal
# let-bindings, so they cannot be overridden piecemeal. Instead of forking the
# whole 1000-line module, this module keeps iso-image.nix (for volumeID,
# squashfs, initrd wiring, kernelParams incl. root=LABEL=...) and mkForce's
# just the two things that define the boot side:
#   - isoImage.contents      -> Limine file layout (kernel/initrd/limine.conf)
#   - system.build.isoImage  -> make-iso9660-image with Limine El Torito images
#
# UEFI config lookup — the hard-learned part (real-hardware Ventoy test):
# Limine checks `<EFI app path>/limine.conf` FIRST; only if absent does it scan
# the boot drive's volumes. Under Ventoy the ISO9660 volume is not reliably
# visible to that scan ("config file not found" on real hardware), so the
# El Torito EFI image is NOT the stock limine-uefi-cd.bin but a custom FAT
# image that carries BOOTX64.EFI + /EFI/BOOT/limine.conf + kernel + initrd.
# boot():/ then refers to that FAT volume itself, so booting never depends on
# the firmware exposing the ISO9660 volume. (~52 MB duplication; same idea as
# upstream's grub efiImg, which nixpkgs also embeds in the ISO.)
#
# BIOS path: limine-bios-cd.bin reads the CD natively; limine-bios.sys +
# limine.conf live in /boot/limine (a standard search path) and the same
# boot():/boot/... paths resolve on the ISO9660 volume, which also carries
# kernel + initrd at /boot. A third limine.conf copy sits at /EFI/BOOT on the
# ISO9660 volume in case a loader launches BOOTX64.EFI straight from the ISO
# tree. The El Torito BIOS image stays under /isolinux because
# make-iso9660-image.sh passes `--sort-weight 1 /isolinux` unconditionally
# when BIOS-bootable and xorriso needs that path to exist.
#
# Not done: `limine bios-install` on the final ISO (what upstream recommends
# for legacy-BIOS boot from a dd'd USB). That would require forking
# make-iso9660-image.sh for a post-xorriso step. BIOS El Torito (real CD,
# Ventoy legacy mode) still works; UEFI USB works via -isohybrid-gpt-basdat.
# finix itself requires UEFI anyway (ADR-002).

{ config, lib, pkgs, ... }:

let
  limine = pkgs.limine.override { buildCDs = true; };

  kernelFile = config.system.boot.loader.kernelFile;
  initrdFile = config.system.boot.loader.initrdFile;
  kernelSource = config.boot.kernelPackages.kernel + "/" + kernelFile;
  initrdSource = config.system.build.initialRamdisk + "/" + initrdFile;

  # Same kernel command line GRUB used: stage-1 finds the ISO by
  # root=LABEL=<volumeID> (already part of boot.kernelParams).
  baseCmdline = "init=${config.system.build.toplevel}/init ${toString config.boot.kernelParams}";

  menuName = "${config.system.nixos.distroName} ${config.system.nixos.label} Installer";

  mkEntry = name: extraParams: ''
    /${name}
        protocol: linux
        path: boot():/boot/${kernelFile}
        cmdline: ${toString ([ baseCmdline ] ++ extraParams)}
        module_path: boot():/boot/${initrdFile}
  '';

  limineConf = pkgs.writeText "limine.conf" ''
    timeout: ${toString (if config.boot.loader.timeout == null then 30 else config.boot.loader.timeout)}
    interface_branding: ${config.system.nixos.distroName} installer
    interface_branding_colour: E33949

    ${mkEntry menuName [ ]}
    ${mkEntry "${menuName} (nomodeset)" [ "nomodeset" ]}
    ${mkEntry "${menuName} (copy to RAM)" [ "copytoram" ]}
    ${mkEntry "${menuName} (debug)" [ "debug" ]}
    ${mkEntry "${menuName} (serial console)" [ "console=ttyS0,115200n8" ]}
  '';

  # Self-contained UEFI El Torito FAT image (see header comment). Determinism
  # care mirrors upstream's efiImg: fixed dates, fixed FAT id, sorted mcopy.
  efiImg =
    pkgs.runCommand "limine-efi-image_eltorito"
      {
        nativeBuildInputs = [
          pkgs.buildPackages.mtools
          pkgs.buildPackages.libfaketime
          pkgs.buildPackages.dosfstools
        ];
        strictDeps = true;
      }
      ''
        mkdir ./contents && cd ./contents
        mkdir -p ./EFI/BOOT ./boot
        cp -p ${limine}/share/limine/BOOTX64.EFI ./EFI/BOOT/BOOTX64.EFI
        cp -p ${limineConf} ./EFI/BOOT/limine.conf
        cp -p ${kernelSource} ./boot/${kernelFile}
        cp -p ${initrdSource} ./boot/${initrdFile}

        find . -exec touch --date=2000-01-01 {} +

        usage_size=$(( $(du -s --block-size=1M --apparent-size . | tr -cd '[:digit:]') * 1024 * 1024 ))
        # 110% of the payload to cover FAT overhead, rounded up to 1M blocks
        image_size=$(( ($usage_size * 110) / 100 ))
        block_size=$((1024*1024))
        image_size=$(( ($image_size / $block_size + 1) * $block_size ))
        echo "Usage size: $usage_size"
        echo "Image size: $image_size"
        truncate --size=$image_size "$out"
        mkfs.vfat --invariant -i 12345678 -n EFIBOOT "$out"

        for d in $(find EFI boot -type d | sort); do
          faketime "2000-01-01 00:00:00" mmd -i "$out" "::/$d"
        done
        for f in $(find EFI boot -type f | sort); do
          mcopy -pvm -i "$out" "$f" "::/$f"
        done

        fsck.vfat -vn "$out"
      '';
in
{
  isoImage.contents = lib.mkForce [
    {
      source = pkgs.writeText "version" config.system.nixos.label;
      target = "/version.txt";
    }
    {
      source = kernelSource;
      target = "/boot/${kernelFile}";
    }
    {
      source = initrdSource;
      target = "/boot/${initrdFile}";
    }
    {
      source = limineConf;
      target = "/boot/limine/limine.conf";
    }
    {
      source = "${limine}/share/limine/limine-bios.sys";
      target = "/boot/limine/limine-bios.sys";
    }
    {
      source = "${limine}/share/limine/limine-bios-cd.bin";
      target = "/isolinux/limine-bios-cd.bin";
    }
    {
      source = efiImg;
      target = "/boot/efi.img";
    }
    {
      source = "${limine}/share/limine/BOOTX64.EFI";
      target = "/EFI/BOOT/BOOTX64.EFI";
    }
    {
      source = limineConf;
      target = "/EFI/BOOT/limine.conf";
    }
  ];

  system.build.isoImage = lib.mkForce (
    pkgs.callPackage "${toString pkgs.path}/nixos/lib/make-iso9660-image.nix" {
      inherit (config.isoImage) compressImage volumeID contents;
      isoName = "${config.image.baseName}.iso";
      bootable = true;
      bootImage = "/isolinux/limine-bios-cd.bin";
      efiBootable = true;
      efiBootImage = "boot/efi.img";
      squashfsContents = config.isoImage.storeContents;
      squashfsCompression = config.isoImage.squashfsCompression;
    }
  );
}
