{
  description = "finix installer ISO";

  # same revisions as calamares-finix-extensions/src/modules/nixos/main.py,
  # so the packages prebuilt into the ISO are the ones the installed system uses
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/e2587caef70cea85dd97d7daab492899902dbf5d";
    finix.url = "github:finix-community/finix/8a9b75a16b6f399e12d031dcd714a938af40c9b5";
    noctalia-src = {
      url = "github:noctalia-dev/noctalia-shell/3d7b9869950592ff7cf3704f6a53afb169d850db";
      flake = false;
    };
    nvwm-src = {
      url = "github:Vifuddyxg/nvwm/58bfe34f14d532b6fdcac3149133cccd2e3bf653";
      flake = false;
    };
    vxwm-src = {
      url = "git+https://codeberg.org/wh1tepearl/vxwm?rev=8b9f04c415a96c92fc36b7639cd1877903f3f0eb";
      flake = false;
    };
    gluewc-src = {
      url = "github:vladbiber/gluewc/0e602ca06e35e6d4f535a077dd89b15c4fdc6f89";
      flake = false;
    };
    glueqs-src = {
      url = "github:vladbiber/glueqs/1c787c3fa8ade2d7fe1148c5f76facdb8313053e";
      flake = false;
    };
    scenefx-src = {
      url = "github:wlrfx/scenefx/37ccd723bef49e6891156ffafce8f549f01446cc";
      flake = false;
    };
    newm-flake.url = "github:jbuchermn/newm/d120fcc390eba70593aecfafbafefe8647fd5c92";
  };

  outputs = inputs @ { self, nixpkgs, finix, noctalia-src, newm-flake, ... }: let
    lib = nixpkgs.lib;

    pkgsTarget = import nixpkgs {
      system = "x86_64-linux";
      config.allowUnfree = true;
    };

    # the two systems the installer can produce with every desktop selected:
    # eudev + elogind (plasma) and mdevd + seatd (everything else)
    mkInstalledSystem = dir: withPlasma: finix.lib.finixSystem {
      inherit (pkgsTarget) lib;

      modules = [
        { nixpkgs.pkgs = lib.mkDefault pkgsTarget; }
        (dir + "/configuration.nix")
        (dir + "/sessions.nix")
        (dir + "/branding.nix")
      ]
      ++ lib.optional withPlasma (dir + "/plasma.nix")
      ++ (with finix.nixosModules; [
        nix-daemon
        chronyd
        bluetooth
        openssh
        sysklogd
        limine
        sudo
        polkit
        getty
        bash
        dhcpcd
        iwd
        regreet
        upower
        labwc
        sway
        niri
        lxqt
        mango
        pipewire
        wireplumber
        rtkit
        xwayland-satellite
        xorg
      ]);

      specialArgs = {
        modulesPath = toString nixpkgs + "/nixos/modules";
        inherit inputs;
      };
    };

    everythingSystem = mkInstalledSystem ./iso/everything-session true;
    everythingMdevdSystem = mkInstalledSystem ./iso/everything-mdevd-session false;

    sessionPackagesOf = cfg: [
      cfg.programs.labwc.package
      cfg.programs.sway.package
      cfg.programs.niri.package
      cfg.programs.mango.package
      cfg.programs.pipewire.package
      cfg.programs.wireplumber.package
      cfg.programs.xorg.package
      cfg.programs.xinit.package
      cfg.programs.xwayland-satellite.package
    ]
    ++ lib.filter (p: lib.elem (p.pname or "") [ "gluewc" "nvwm" "vxwm" ]) cfg.environment.systemPackages;

    prebuiltSessionPackages =
      sessionPackagesOf everythingMdevdSystem.config
      ++ sessionPackagesOf everythingSystem.config
      ++ [
        (pkgsTarget.callPackage (noctalia-src + "/nix/package.nix") { })
        newm-flake.packages.x86_64-linux.newm
        pkgsTarget.quickshell
        pkgsTarget.rofi
      ];
  in {
    nixosConfigurations.finix-iso = lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = {
        finixPrebuiltSessions = prebuiltSessionPackages;
      };
      modules = [
        "${nixpkgs}/nixos/modules/installer/cd-dvd/installation-cd-graphical-calamares-plasma6.nix"
        ./iso/finix-iso.nix
      ];
    };

    packages.x86_64-linux.prebuilt-sessions = pkgsTarget.linkFarm "finix-prebuilt-sessions" (
      lib.imap0 (i: p: {
        name = "${toString i}-${p.pname or p.name}";
        path = p;
      }) prebuiltSessionPackages
    );

    packages.x86_64-linux.everything-toplevel =
      everythingSystem.config.system.build.toplevel;
    packages.x86_64-linux.everything-mdevd-toplevel =
      everythingMdevdSystem.config.system.build.toplevel;

    packages.x86_64-linux.iso =
      self.nixosConfigurations.finix-iso.config.system.build.isoImage;
  };
}
