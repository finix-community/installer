{
  description = "Finix system (installed by the Finix installer)";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    # Illustrative sample: unpinned for readability. A real install pins
    # every input to the revisions the ISO was built from (see main.py).
    finix.url = "github:finix-community/finix";
  };

  outputs = inputs @ { self, nixpkgs, finix, ... }: let
    pkgs = import nixpkgs {
      system = "x86_64-linux";
      config.allowUnfree = true;
    };
  in {
    nixosConfigurations.finixos = finix.lib.finixSystem {
      inherit (pkgs) lib;

      modules = with finix.nixosModules; [
        { nixpkgs.pkgs = nixpkgs.lib.mkDefault pkgs; }
        (./configuration.nix)
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
        # session/desktop modules (enable-gated; configuration.nix picks one)
        labwc
        sway
        niri
        hyprland
        lxqt
      ];

      specialArgs = {
        modulesPath = toString nixpkgs + "/nixos/modules";
      };
    };
  };
}
