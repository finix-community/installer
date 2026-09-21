# limine boot menu group named finix instead of NixOS
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
      sed -e "s|/+NixOS {group_name}|/+finix {group_name}|" \
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
