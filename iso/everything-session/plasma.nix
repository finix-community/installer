# KDE Plasma 6 on finix (from the finix modules/plasma branch)
{
  config,
  pkgs,
  lib,
  ...
}:
let
  cfg = config.programs.plasma;

  inherit (pkgs) kdePackages;

  sessionScript = pkgs.writeShellScript "plasma-session" ''
    ${config.programs.pipewire.package}/bin/pipewire &
    ${config.programs.wireplumber.package}/bin/wireplumber &
    ${config.programs.pipewire.package}/bin/pipewire-pulse &
    ${kdePackages.kservice}/bin/kbuildsycoca6 || true
    exec ${kdePackages.plasma-workspace}/bin/startplasma-wayland \
      >"$HOME/plasma.log" 2>&1
  '';

  sessionFile = pkgs.writeTextDir "share/wayland-sessions/plasma.desktop" ''
    [Desktop Entry]
    Name=Plasma (Wayland)
    Comment=KDE Plasma Desktop
    Exec=${pkgs.dbus}/bin/dbus-run-session -- ${sessionScript}
    Type=Application
    DesktopNames=KDE
  '';

  lnfMetadata = pkgs.writeTextDir "share/plasma/look-and-feel/org.finix.desktop/metadata.json" (
    builtins.toJSON {
      KPackageStructure = "Plasma/LookAndFeel";
      KPlugin = {
        Id = "org.finix.desktop";
        Name = "finix";
        Description = "Breeze Dark with the finix wallpaper";
      };
      "X-Plasma-APIVersion" = "2";
    }
  );
  lnfDefaults = pkgs.writeTextDir "share/plasma/look-and-feel/org.finix.desktop/contents/defaults" ''
    [kdeglobals][KDE]
    widgetStyle=Breeze
    [kdeglobals][General]
    ColorScheme=BreezeDark
    [kdeglobals][Icons]
    Theme=breeze-dark
    [plasmarc][Theme]
    name=default
    [Wallpaper]
    Image=/etc/finix/wallpaper.png
  '';
in
{
  options.programs.plasma = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Whether to enable the KDE Plasma 6 Wayland session.";
    };
  };

  config = lib.mkIf cfg.enable {
    # kwin needs /tmp/.X11-unix to exist before it starts xwayland
    finit.tmpfiles.rules = [
      "D! /tmp/.X11-unix  1777 root root"
      "z  /tmp/.X11-unix"
    ];

    services.upower.enable = true;

    environment.systemPackages = with kdePackages; [
      (lib.hiPrio sessionFile)

      qtwayland
      qtsvg
      qtimageformats

      kwin
      pkgs.xwayland

      plasma-workspace
      plasma-desktop
      kscreen
      libkscreen
      kscreenlocker
      kactivitymanagerd
      kglobalacceld
      kwrited
      baloo
      milou
      kmenuedit
      kinfocenter
      plasma-systemmonitor
      ksystemstats
      libksysguard
      systemsettings
      kcmutils
      kdeplasma-addons
      pkgs.xdg-user-dirs

      frameworkintegration
      kauth
      kcoreaddons
      kded
      kfilemetadata
      kguiaddons
      kiconthemes
      kimageformats
      kio
      kio-admin
      kio-extras
      kio-fuse
      knighttime
      kpackage
      kservice
      kunifiedpush
      solid
      plasma-activities
      phonon-vlc

      libplasma
      qqc2-desktop-style
      kde-cli-tools

      breeze
      breeze-icons
      breeze-gtk
      kde-gtk-config
      ocean-sound-theme
      pkgs.hicolor-icon-theme
      qqc2-breeze-style
      lnfMetadata
      lnfDefaults

      polkit-kde-agent-1
      plasma-integration
      drkonqi

      plasma-pa
      powerdevil
      pkgs.iwgtk

      kwallet
      kwalletmanager

      dolphin
      konsole
      kate
      ark
      gwenview
      okular
      spectacle
      kdegraphics-thumbnailers
    ];

    environment.pathsToLink = [
      "/share"
      "/libexec"
    ];

    security.pam.environment =
      let
        qtVersions = with pkgs; [
          qt5
          qt6
        ];
      in
      {
        QT_PLUGIN_PATH.default = map (qt: "/run/current-system/sw/${qt.qtbase.qtPluginPrefix}") qtVersions;
        QML2_IMPORT_PATH.default = map (qt: "/run/current-system/sw/${qt.qtbase.qtQmlPrefix}") qtVersions;

        XDG_CONFIG_DIRS.default = [
          "@{HOME}/.config/kdedefaults"
          "/etc/xdg"
        ];

        KPACKAGE_DEP_RESOLVERS_PATH.default = [
          "${kdePackages.frameworkintegration.out}/libexec/kf6/kpackagehandlers"
        ];
      };

    environment.etc."xdg/kdeglobals".text = ''
      [KDE]
      LookAndFeelPackage=org.finix.desktop
    '';

    security.pam.services.kde.text = ''
      auth      substack      login
      account   include       login
      password  substack      login
      session   include       login
    '';

    security.wrappers = {
      kwin_wayland = {
        owner = "root";
        group = "root";
        capabilities = "cap_sys_nice+ep";
        source = "${lib.getBin pkgs.kdePackages.kwin}/bin/kwin_wayland";
      };
    };

    xdg.portal.portals = [
      pkgs.kdePackages.xdg-desktop-portal-kde
      pkgs.xdg-desktop-portal-gtk
    ];
  };
}
