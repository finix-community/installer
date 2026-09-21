# finix system configuration
# rebuild: sudo finix-rebuild switch

{ config, pkgs, ... }:

{
  imports = [ ./hardware-configuration.nix ];

  finit.runlevel = 3;
  finit.services.nix-daemon.environment.CURL_CA_BUNDLE = config.security.pki.caBundle;
  services.nix-daemon.enable = true;
  services.nix-daemon.settings.experimental-features = [ "nix-command" "flakes" ];
  services.nix-daemon.settings.trusted-users = [ "root" "@wheel" ];

  services.dbus.enable = true;
  services.sysklogd.enable = true;
  services.polkit.enable = true;
  services.chrony.enable = true;
  services.bluetooth.enable = true;

  programs.sudo.enable = true;
  programs.bash.enable = true;
  hardware.graphics.enable = true;
  fonts.fontconfig.enable = true;
  fonts.enableDefaultPackages = true;

  # bootloader
  programs.limine.enable = true;
  programs.limine.efiSupport = true;
  programs.limine.settings.editor_enabled = true;
  programs.limine.settings.wallpaper = [ ];
  boot.loader.efi.canTouchEfiVariables = true;

  # low-RAM machine: one build at a time
  services.nix-daemon.settings.max-jobs = 1;
  services.nix-daemon.settings.cores = 4;

  services.mdevd.enable = true;
  services.seatd.enable = true;

  # network: dhcpcd + iwd (iwctl for wifi)
  services.dhcpcd.enable = true;
  services.dhcpcd.extraArgs = [ "--noipv6rs" ];
  services.iwd.enable = true;
  programs.resolvconf.enable = true;
  programs.resolvconf.settings.name_servers_append = [ "1.1.1.1" "1.0.0.1" ];
  programs.resolvconf.settings.resolv_conf_options = [ "timeout:2" "attempts:2" ];
  programs.resolvconf.settings.libc_restart = "true";
  networking.hostName = "finix";

  time.timeZone = "Europe/Bucharest";
  i18n.defaultLocale = "en_US.UTF-8";

  # login
  programs.regreet.enable = true;
  programs.regreet.compositor.environment.XDG_DATA_DIRS = "/run/current-system/sw/share";
  programs.regreet.settings.background = {
    path = "/etc/finix/wallpaper.png";
    fit = "Cover";
  };
  programs.regreet.settings.GTK.application_prefer_dark_theme = true;
  services.greetd.settings.terminal.vt = 1;
  services.getty.ttys = [ "tty2" "tty3" "tty4" "tty5" "tty6" ];

  # audio
  programs.pipewire.enable = true;
  programs.pipewire.alsa.enable = true;
  programs.wireplumber.enable = true;
  services.rtkit.enable = true;
  users.groups.audio.gid = config.ids.gids.audio;

  # desktop
  programs.labwc.enable = true;
  programs.lxqt.enable = true;
  programs.sway.enable = true;
  programs.niri.enable = true;
  programs.xwayland-satellite.enable = true;
  programs.xorg.enable = true;
  programs.xinit.enable = true;
  programs.mango.enable = true;

  users.users."tester" = {
    isNormalUser = true;
    description = "Tester";
    extraGroups = [ "wheel" "video" "audio" config.services.seatd.group ];
  };

  environment.systemPackages = with pkgs; [
    vim
    git
    wget
    iproute2
    iputils
    pciutils
    shadow
    foot
    firefox
    (lib.hiPrio (writeShellScriptBin "finix-rebuild" ''
      set -e
      ${git}/bin/git -C /etc/finix add -A
      exec ${nixos-rebuild}/bin/nixos-rebuild "''${1:-switch}" --flake /etc/finix#finixos "''${@:2}"
    ''))
    fastfetch
    (writeShellScriptBin "neofetch" ''
      exec env distro="finix $(uname -m)" ${hyfetch}/bin/neowofetch --ascii_distro nixos --ascii_colors 1 8 1 8 1 8 "$@"
    '')
  ];

  environment.etc."xdg/fastfetch/config.jsonc".text = builtins.toJSON {
    logo = {
      source = "nixos";
      color = {
        "1" = "31";
        "2" = "90";
        "3" = "31";
        "4" = "90";
        "5" = "31";
        "6" = "90";
      };
    };
    modules = [
      "title" "separator" "os" "host" "kernel" "uptime" "packages" "shell"
      "display" "de" "wm" "wmtheme" "theme" "icons" "font" "cursor"
      "terminal" "terminalfont" "cpu" "gpu" "memory" "swap" "disk"
      "localip" "battery" "poweradapter" "locale" "break" "colors"
    ];
  };

  # services.openssh.enable = true;
}
