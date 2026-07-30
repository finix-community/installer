{
  description = "finix installer ISO — graphical Calamares live image (finix-iso baseline)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    # Pinned to the exact revisions the installer (main.py) writes into the
    # generated system flake — keep these in sync with NIXPKGS_REV & friends
    # in calamares-finix-extensions/src/modules/nixos/main.py. They are used
    # to pre-build the from-source session packages into the live ISO's store
    # so that installation on low-end machines copies instead of compiling.
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
    # newm is a flake with its OWN lock and deliberately NO follows: it only
    # builds against the old nixpkgs its lockfile pins.
    newm-flake.url = "github:jbuchermn/newm/d120fcc390eba70593aecfafbafefe8647fd5c92";
  };

  outputs = inputs @ { self, nixpkgs, finix, noctalia-src, nvwm-src, vxwm-src, newm-flake }: let
    # Same pkgs instantiation as the generated /etc/finix/flake.nix — package
    # identity (store paths) must match what the installed system evaluates.
    pkgsTarget = import nixpkgs {
      system = "x86_64-linux";
      config.allowUnfree = true;
    };

    # The installer produces exactly two system flavors (see main.py):
    #   - mdevd + seatd  (finix default; compositors/PipeWire are rebuilt
    #     from source against libudev-zero — the EXPENSIVE builds)
    #   - eudev + elogind (whenever KDE Plasma is selected; elogind's
    #     TakeDevice needs the udev database, so mdevd is out — mostly
    #     stock cached packages plus a custom xorg-server-with-eudev)
    # Both "everything" systems are evaluated here ONLY to reference the
    # exact per-session packages for pre-building into the ISO. Files are
    # vendored from the installer's render gate into iso/everything-session/
    # (all 11 sessions => eudev flavor) and iso/everything-mdevd-session/
    # (all except plasma => mdevd flavor).
    mkInstalledSystem = dir: withPlasma: finix.lib.finixSystem {
      inherit (pkgsTarget) lib;

      modules = [
        { nixpkgs.pkgs = nixpkgs.lib.mkDefault pkgsTarget; }
        (dir + "/configuration.nix")
        (dir + "/sessions.nix")
        (dir + "/branding.nix")
      ]
      ++ nixpkgs.lib.optional withPlasma (dir + "/plasma.nix")
      ++ (with finix.nixosModules; [
        nix-daemon
        openssh
        sysklogd
        limine
        sudo
        polkit
        getty
        bash
        dhcpcd
        iwd
        greetd
        networkmanager
        sddm
        upower
        labwc
        sway
        niri
        hyprland
        lxqt
        mango
        pipewire
        wireplumber
        rtkit
        xwayland-satellite
        xorg
        xinit
      ]);

      specialArgs = {
        modulesPath = toString nixpkgs + "/nixos/modules";
        inherit inputs;
      };
    };

    everythingSystem = mkInstalledSystem ./iso/everything-session true;
    everythingMdevdSystem = mkInstalledSystem ./iso/everything-mdevd-session false;

    ecfg = everythingSystem.config;
    mcfg = everythingMdevdSystem.config;

    # Replicas of the installer's sessions.nix builds (same pkgs, same src,
    # same arguments => identical store paths).
    noctaliaPkg = pkgsTarget.callPackage (noctalia-src + "/nix/package.nix") { };
    nvwmPkg = pkgsTarget.stdenv.mkDerivation {
      pname = "nvwm";
      version = "0-unstable-pinned";
      src = nvwm-src;
      buildInputs = with pkgsTarget; [
        libx11
        libxinerama
        libxrandr
        libxcomposite
        libxrender
      ];
      makeFlags = [
        "PREFIX=${placeholder "out"}"
        "SYSCONFDIR=${placeholder "out"}/etc"
      ];
    };

    # Per-session packages a flavor resolves. Under mdevd these are the
    # from-source libudev-zero rebuilds; under eudev they are mostly stock
    # (cached) plus the custom xorg-server-with-eudev. Embedding BOTH sets
    # in the ISO store means nixos-install copies instead of compiling,
    # whatever the user selects — critical for low-RAM machines.
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
    ];

    # Replica of the installer's vxwm build (same pkgs, same src, same
    # arguments => identical store path).
    vxwmPkg = pkgsTarget.stdenv.mkDerivation {
      pname = "vxwm";
      version = "2.3-pinned";
      src = vxwm-src;
      buildInputs = with pkgsTarget; [
        libx11
        libxft
        libxinerama
        fontconfig
        freetype
      ];
      makeFlags = [
        "PREFIX=${placeholder "out"}"
        "X11INC=${pkgsTarget.libx11.dev}/include"
        "X11LIB=${pkgsTarget.libx11}/lib"
        "FREETYPEINC=${pkgsTarget.freetype.dev}/include/freetype2"
      ];
    };

    prebuiltSessionPackages = sessionPackagesOf mcfg ++ sessionPackagesOf ecfg ++ [
      noctaliaPkg
      nvwmPkg
      vxwmPkg
      # newm's whole closure (its own old-nixpkgs python/wlroots) — huge win
      # to pre-embed: the target would otherwise build all of it from source
      newm-flake.packages.x86_64-linux.newm
      # not substitutable from cache.nixos.org on this pin
      pkgsTarget.rofi
    ];
  in {
    nixosConfigurations.finix-iso = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = {
        finixPrebuiltSessions = prebuiltSessionPackages;
      };
      modules = [
        "${nixpkgs}/nixos/modules/installer/cd-dvd/installation-cd-graphical-calamares-plasma6.nix"
        ./iso/finix-iso.nix
      ];
    };

    # Exposed for local pre-building / verification. (Indexed names: the two
    # flavors contain same-named packages with different store paths.)
    packages.x86_64-linux.prebuilt-sessions = pkgsTarget.linkFarm "finix-prebuilt-sessions" (
      nixpkgs.lib.imap0 (i: p: {
        name = "${toString i}-${p.pname or p.name}";
        path = p;
      }) prebuiltSessionPackages
    );

    # The per-flavor toplevels, for verifying that no heavy source builds
    # remain once the prebuilt set is realized (nix-store --dry-run).
    packages.x86_64-linux.everything-toplevel =
      everythingSystem.config.system.build.toplevel;
    packages.x86_64-linux.everything-mdevd-toplevel =
      everythingMdevdSystem.config.system.build.toplevel;

    packages.x86_64-linux.iso =
      self.nixosConfigurations.finix-iso.config.system.build.isoImage;
  };
}
