{
  config,
  pkgs,
  lib,
  inputs,
  ...
}:
let
  audioStart = ''
    ${config.programs.pipewire.package}/bin/pipewire &
    ${config.programs.wireplumber.package}/bin/wireplumber &
    ${config.programs.pipewire.package}/bin/pipewire-pulse &
  '';

  noctalia = pkgs.callPackage (inputs.noctalia-src + "/nix/package.nix") { };

  session-labwc-noctalia = pkgs.writeShellScript "session-labwc-noctalia" ''
    ${config.programs.labwc.package}/bin/labwc >"$XDG_RUNTIME_DIR/labwc-compositor.log" 2>&1 &
    comp=$!
    sock=""
    i=0
    while [ $i -lt 100 ]; do
      for s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$s" in
          *.lock) ;;
          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;
        esac
      done
      [ -n "$sock" ] && break
      i=$((i + 1))
      sleep 0.1
    done
    if [ -n "$sock" ]; then
      export WAYLAND_DISPLAY="$sock"
      export DISPLAY=:0
      ${pkgs.swaybg}/bin/swaybg -i /etc/finix/wallpaper.png -m fill &
      ${audioStart}
      (
        ${noctalia}/bin/noctalia --daemon >"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        np=$!
        sleep 5
        if ! kill -0 "$np" 2>/dev/null; then
          echo "noctalia exited early; retrying with software rendering" \
            >>"$XDG_RUNTIME_DIR/noctalia.log"
          QT_QUICK_BACKEND=software LIBGL_ALWAYS_SOFTWARE=1 \
            ${noctalia}/bin/noctalia --daemon \
            >>"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        fi
      ) &
    fi
    wait "$comp"
  '';

  session-sway-noctalia = pkgs.writeShellScript "session-sway-noctalia" ''
    ${config.programs.sway.package}/bin/sway -c /etc/sway/config-noctalia >"$XDG_RUNTIME_DIR/sway-compositor.log" 2>&1 &
    comp=$!
    sock=""
    i=0
    while [ $i -lt 100 ]; do
      for s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$s" in
          *.lock) ;;
          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;
        esac
      done
      [ -n "$sock" ] && break
      i=$((i + 1))
      sleep 0.1
    done
    if [ -n "$sock" ]; then
      export WAYLAND_DISPLAY="$sock"
      export DISPLAY=:0
      ${pkgs.swaybg}/bin/swaybg -i /etc/finix/wallpaper.png -m fill &
      ${audioStart}
      (
        ${noctalia}/bin/noctalia --daemon >"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        np=$!
        sleep 5
        if ! kill -0 "$np" 2>/dev/null; then
          echo "noctalia exited early; retrying with software rendering" \
            >>"$XDG_RUNTIME_DIR/noctalia.log"
          QT_QUICK_BACKEND=software LIBGL_ALWAYS_SOFTWARE=1 \
            ${noctalia}/bin/noctalia --daemon \
            >>"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        fi
      ) &
    fi
    wait "$comp"
  '';

  session-niri-noctalia = pkgs.writeShellScript "session-niri-noctalia" ''
    ${config.programs.niri.package}/bin/niri --session >"$XDG_RUNTIME_DIR/niri-compositor.log" 2>&1 &
    comp=$!
    sock=""
    i=0
    while [ $i -lt 100 ]; do
      for s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$s" in
          *.lock) ;;
          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;
        esac
      done
      [ -n "$sock" ] && break
      i=$((i + 1))
      sleep 0.1
    done
    if [ -n "$sock" ]; then
      export WAYLAND_DISPLAY="$sock"
      export DISPLAY=:0
      i=0
      while [ $i -lt 20 ]; do
        for ns in "$XDG_RUNTIME_DIR"/niri.*.sock; do
          if [ -S "$ns" ]; then export NIRI_SOCKET="$ns"; break 2; fi
        done
        i=$((i + 1))
        sleep 0.1
      done
      ${pkgs.swaybg}/bin/swaybg -i /etc/finix/wallpaper.png -m fill &
      ${audioStart}
      (
        ${noctalia}/bin/noctalia --daemon >"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        np=$!
        sleep 5
        if ! kill -0 "$np" 2>/dev/null; then
          echo "noctalia exited early; retrying with software rendering" \
            >>"$XDG_RUNTIME_DIR/noctalia.log"
          QT_QUICK_BACKEND=software LIBGL_ALWAYS_SOFTWARE=1 \
            ${noctalia}/bin/noctalia --daemon \
            >>"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        fi
      ) &
    fi
    wait "$comp"
  '';

  session-mango-noctalia = pkgs.writeShellScript "session-mango-noctalia" ''
    ${config.programs.mango.package}/bin/mango >"$XDG_RUNTIME_DIR/mango-compositor.log" 2>&1 &
    comp=$!
    sock=""
    i=0
    while [ $i -lt 100 ]; do
      for s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$s" in
          *.lock) ;;
          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;
        esac
      done
      [ -n "$sock" ] && break
      i=$((i + 1))
      sleep 0.1
    done
    if [ -n "$sock" ]; then
      export WAYLAND_DISPLAY="$sock"
      export DISPLAY=:0
      ${pkgs.swaybg}/bin/swaybg -i /etc/finix/wallpaper.png -m fill &
      ${audioStart}
      (
        ${noctalia}/bin/noctalia --daemon >"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        np=$!
        sleep 5
        if ! kill -0 "$np" 2>/dev/null; then
          echo "noctalia exited early; retrying with software rendering" \
            >>"$XDG_RUNTIME_DIR/noctalia.log"
          QT_QUICK_BACKEND=software LIBGL_ALWAYS_SOFTWARE=1 \
            ${noctalia}/bin/noctalia --daemon \
            >>"$XDG_RUNTIME_DIR/noctalia.log" 2>&1 &
        fi
      ) &
    fi
    wait "$comp"
  '';

  session-labwc = pkgs.writeShellScript "session-labwc" ''
    ${audioStart}
    exec ${config.programs.labwc.package}/bin/labwc
  '';

  session-sway = pkgs.writeShellScript "session-sway" ''
    ${audioStart}
    exec ${config.programs.sway.package}/bin/sway
  '';

  session-niri = pkgs.writeShellScript "session-niri" ''
    ${audioStart}
    exec ${config.programs.niri.package}/bin/niri --session
  '';

  session-mango = pkgs.writeShellScript "session-mango" ''
    ${audioStart}
    exec ${config.programs.mango.package}/bin/mango
  '';

  gluewcUdev =
    if config.services.mdevd.enable || config.services.keventd.enable then
      pkgs.libudev-zero
    else
      null;
  gluewcLibinput = pkgs.libinput.override (
    lib.optionalAttrs (gluewcUdev != null) {
      udev = gluewcUdev;
      wacomSupport = false;
    }
  );
  gluewcWlroots = pkgs.wlroots_0_20.override { libinput = gluewcLibinput; };
  scenefx = pkgs.stdenv.mkDerivation {
    pname = "scenefx";
    version = "0.5.0";
    src = inputs.scenefx-src;
    strictDeps = true;
    depsBuildBuild = [ pkgs.pkg-config ];
    nativeBuildInputs = with pkgs; [
      meson
      ninja
      pkg-config
      scdoc
      wayland-scanner
    ];
    buildInputs = with pkgs; [
      gluewcWlroots
      wayland
      wayland-protocols
      libdrm
      libxkbcommon
      pixman
      libGL
      libgbm
      libxcb
      libxcb-wm
    ];
    mesonFlags = [ "-Dexamples=false" "-Dwerror=false" ];
  };
  gluewc = pkgs.stdenv.mkDerivation {
    pname = "gluewc";
    version = "0.3.0";
    src = inputs.gluewc-src;
    strictDeps = true;
    nativeBuildInputs = with pkgs; [
      pkg-config
      wayland-scanner
      makeWrapper
    ];
    buildInputs = with pkgs; [
      gluewcWlroots
      gluewcLibinput
      scenefx
      wayland
      wayland-protocols
      libxkbcommon
      pixman
      libdrm
      libGL
      libgbm
      seatd
      libxcb
      libxcb-wm
    ];
    makeFlags = [
      "PREFIX=${placeholder "out"}"
      "SESSIONDIR=${placeholder "out"}/share/wayland-sessions"
      "VERSION=0.3.0"
      "WAYLAND_SCANNER=wayland-scanner"
    ];
    postInstall = ''
      wrapProgram $out/bin/gluewc-session \
        --set-default GLUEWC_DATADIR $out/share/gluewc \
        --prefix PATH : ${
          lib.makeBinPath [
            pkgs.dbus
            config.programs.pipewire.package
            config.programs.wireplumber.package
            pkgs.xwayland
            pkgs.procps
          ]
        }:$out/bin
    '';
  };

  session-gluewc = pkgs.writeShellScript "session-gluewc" ''
    ${gluewc}/bin/gluewc-session &
    comp=$!
    sock=""
    i=0
    while [ $i -lt 100 ]; do
      for s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$s" in
          *.lock) ;;
          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;
        esac
      done
      [ -n "$sock" ] && break
      i=$((i + 1))
      sleep 0.1
    done
    if [ -n "$sock" ]; then
      export WAYLAND_DISPLAY="$sock"
      export DISPLAY=:0
      ${pkgs.swaybg}/bin/swaybg -i /etc/finix/wallpaper.png -m fill &
    fi
    wait "$comp"
  '';

  glueqsConfig = pkgs.runCommand "glueqs-config" { nativeBuildInputs = [ pkgs.jq ]; } ''
    cp -r ${inputs.glueqs-src} $out
    chmod -R u+w $out
    jq '.wallpaper = "/etc/finix/wallpaper.png" | .dockUsage = ""' ${inputs.glueqs-src}/settings.json > $out/settings.json
  '';

  session-gluewc-glueqs = pkgs.writeShellScript "session-gluewc-glueqs" ''
    d="''${XDG_CONFIG_HOME:-$HOME/.config}/quickshell/glueqs"
    if [ ! -e "$d" ]; then
      mkdir -p "$(dirname "$d")"
      cp -rL ${glueqsConfig} "$d"
      chmod -R u+w "$d"
    fi
    ${gluewc}/bin/gluewc-session &
    comp=$!
    sock=""
    i=0
    while [ $i -lt 100 ]; do
      for s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$s" in
          *.lock) ;;
          *) if [ -S "$s" ]; then sock="$(basename "$s")"; break; fi ;;
        esac
      done
      [ -n "$sock" ] && break
      i=$((i + 1))
      sleep 0.1
    done
    if [ -n "$sock" ]; then
      export WAYLAND_DISPLAY="$sock"
      export DISPLAY=:0
      ${pkgs.quickshell}/bin/qs -c glueqs >"$XDG_RUNTIME_DIR/glueqs.log" 2>&1 &
    fi
    wait "$comp"
  '';

  nvwm = pkgs.stdenv.mkDerivation {
    pname = "nvwm";
    version = "0-unstable-pinned";
    src = inputs.nvwm-src;
    buildInputs = with pkgs; [
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

  session-nvwm = pkgs.writeShellScript "session-nvwm" ''
    ${pkgs.xwallpaper}/bin/xwallpaper --zoom /etc/finix/wallpaper.png &
    ${audioStart}
    exec ${nvwm}/bin/nvwm
  '';

  swayConfigBase = "${config.programs.sway.package}/etc/sway/config";
  swayWallpaper = "output * bg /etc/finix/wallpaper.png fill";
  swayConfig = pkgs.runCommand "sway-config" { } ''
    cat ${swayConfigBase} > $out
    echo "${swayWallpaper}" >> $out
  '';
  swayConfigNoctalia = pkgs.runCommand "sway-config-noctalia" { } ''
    sed "/^bar {/,$ d" ${swayConfigBase} > $out
    echo "${swayWallpaper}" >> $out
  '';

  vxwm = pkgs.stdenv.mkDerivation {
    pname = "vxwm";
    version = "2.3-pinned";
    src = inputs.vxwm-src;
    buildInputs = with pkgs; [
      libx11
      libxft
      libxinerama
      fontconfig
      freetype
    ];
    makeFlags = [
      "PREFIX=${placeholder "out"}"
      "X11INC=${pkgs.libx11.dev}/include"
      "X11LIB=${pkgs.libx11}/lib"
      "FREETYPEINC=${pkgs.freetype.dev}/include/freetype2"
    ];
  };

  session-vxwm = pkgs.writeShellScript "session-vxwm" ''
    ${pkgs.xwallpaper}/bin/xwallpaper --zoom /etc/finix/wallpaper.png &
    ${audioStart}
    exec ${vxwm}/bin/vxwm
  '';

  session-newm = pkgs.writeShellScript "session-newm" ''
    ${audioStart}
    exec ${inputs.newm-flake.packages.x86_64-linux.newm}/bin/start-newm
  '';

  seed-user-configs = pkgs.writeShellScript "seed-user-configs" ''
    export PATH=${pkgs.coreutils}/bin:$PATH
    seed() {
      [ -e "$1" ] || return 0
      [ -e "$2" ] && return 0
      mkdir -p "$(dirname "$2")"
      cp -rL "$1" "$2" || return 0
      chmod -R u+w "$2"
    }
    while IFS=: read -r user _ uid gid _ home _; do
      [ "$uid" -ge 1000 ] && [ "$uid" -lt 65000 ] || continue
      [ -d "$home" ] || continue
      h="$home"
      seed "/etc/xdg/labwc" "$h/.config/labwc"
      seed "/etc/sway/config" "$h/.config/sway/config"
      seed "/etc/mango/config.conf" "$h/.config/mango/config.conf"
      seed "/etc/nvwm/config.conf" "$h/.config/nvwm/config.conf"
      chown -R "$uid:$gid" "$h/.config" 2>/dev/null || true
    done < /etc/passwd
  '';
in
{
  environment.systemPackages = [
    (pkgs.writeTextDir "share/wayland-sessions/labwc-noctalia.desktop" ''
      [Desktop Entry]
      Name=Labwc + Noctalia
      Comment=labwc stacking compositor with the Noctalia desktop shell
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-labwc-noctalia}
      Type=Application
      DesktopNames=labwc;wlroots
    '')
    (pkgs.writeTextDir "share/wayland-sessions/sway-noctalia.desktop" ''
      [Desktop Entry]
      Name=Sway + Noctalia
      Comment=Sway i3-compatible compositor with the Noctalia desktop shell
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-sway-noctalia}
      Type=Application
      DesktopNames=sway;wlroots
    '')
    (pkgs.writeTextDir "share/wayland-sessions/niri-noctalia.desktop" ''
      [Desktop Entry]
      Name=Niri + Noctalia
      Comment=Niri scrollable-tiling compositor with the Noctalia desktop shell
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-niri-noctalia}
      Type=Application
      DesktopNames=niri
    '')
    (pkgs.writeTextDir "share/wayland-sessions/mango-noctalia.desktop" ''
      [Desktop Entry]
      Name=Mango + Noctalia
      Comment=Mango tiling compositor with the Noctalia desktop shell
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-mango-noctalia}
      Type=Application
      DesktopNames=mango;wlroots
    '')
    (lib.setPrio (-10) (pkgs.writeTextDir "share/wayland-sessions/labwc.desktop" ''
      [Desktop Entry]
      Name=Labwc
      Comment=labwc stacking compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-labwc}
      Type=Application
      DesktopNames=labwc;wlroots
    ''))
    (lib.setPrio (-10) (pkgs.writeTextDir "share/wayland-sessions/sway.desktop" ''
      [Desktop Entry]
      Name=Sway
      Comment=Sway i3-compatible compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-sway}
      Type=Application
      DesktopNames=sway;wlroots
    ''))
    (lib.setPrio (-10) (pkgs.writeTextDir "share/wayland-sessions/niri.desktop" ''
      [Desktop Entry]
      Name=Niri
      Comment=Niri scrollable-tiling compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-niri}
      Type=Application
      DesktopNames=niri
    ''))
    (lib.setPrio (-10) (pkgs.writeTextDir "share/wayland-sessions/mango.desktop" ''
      [Desktop Entry]
      Name=Mango
      Comment=Mango tiling compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-mango}
      Type=Application
      DesktopNames=mango;wlroots
    ''))
    gluewc
    pkgs.alacritty
    pkgs.rofi
    pkgs.grim
    pkgs.slurp
    pkgs.wl-clipboard
    (lib.setPrio (-20) (pkgs.writeTextDir "share/wayland-sessions/gluewc.desktop" ''
      [Desktop Entry]
      Name=gluewc
      Comment=Animated BSP Wayland compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-gluewc}
      Type=Application
      DesktopNames=gluewc
    ''))
    pkgs.swaybg
    (lib.setPrio (-20) (pkgs.writeTextDir "share/wayland-sessions/gluewc-glueqs.desktop" ''
      [Desktop Entry]
      Name=gluewc + glueqs
      Comment=Animated BSP Wayland compositor with the glueqs bar
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-gluewc-glueqs}
      Type=Application
      DesktopNames=gluewc
    ''))
    pkgs.quickshell
    pkgs.curl
    pkgs.bluez
    pkgs.procps
    (pkgs.writeTextDir "share/xsessions/nvwm.desktop" ''
      [Desktop Entry]
      Name=NVWM
      Comment=Vim-inspired tiling X11 window manager
      Exec=${pkgs.dbus}/bin/dbus-run-session ${session-nvwm}
      Type=Application
      DesktopNames=nvwm
    '')
    pkgs.alacritty
    pkgs.rofi
    pkgs.maim
    nvwm
    vxwm
    (pkgs.writeTextDir "share/xsessions/vxwm.desktop" ''
      [Desktop Entry]
      Name=vxwm
      Comment=Versatile dwm-style X11 tiling window manager
      Exec=${pkgs.dbus}/bin/dbus-run-session ${session-vxwm}
      Type=Application
      DesktopNames=vxwm
    '')
    pkgs.st
    pkgs.dmenu
    inputs.newm-flake.packages.x86_64-linux.newm
    (pkgs.writeTextDir "share/wayland-sessions/newm.desktop" ''
      [Desktop Entry]
      Name=newm
      Comment=Touchpad-centric Wayland compositor
      Exec=${pkgs.dbus}/bin/dbus-run-session -- ${session-newm}
      Type=Application
      DesktopNames=newm
    '')
    pkgs.alacritty
    pkgs.wob
    pkgs.pulseaudio
    pkgs.alacritty
    pkgs.fuzzel
    pkgs.rofi
    pkgs.swaybg
  ];
  environment.etc."nvwm/config.conf".source = "${nvwm}/etc/nvwm/config.conf";
  environment.etc."mango/config.conf".source =
    config.programs.mango.package.src + "/assets/config.conf";
  environment.etc."xdg/labwc/rc.xml".source =
    config.programs.labwc.package.src + "/docs/rc.xml";
  environment.etc."xdg/labwc/menu.xml".source =
    config.programs.labwc.package.src + "/docs/menu.xml";
  environment.etc."xdg/labwc/autostart".text = ''
      # copy /etc/xdg/labwc to ~/.config/labwc to customize
      swaybg -i /etc/finix/wallpaper.png -m fill >/dev/null 2>&1 &
  '';
  environment.etc."sway/config".source = swayConfig;
  environment.etc."xdg/sway/config".source = swayConfig;
  environment.etc."sway/config-noctalia".source = swayConfigNoctalia;
  environment.pathsToLink = [ "/share/applications" "/share/xsessions" ];
  xdg.icons.enable = true;
  security.wrappers.X.enable = lib.mkForce true;
  system.activation.scripts.seed-user-configs = {
    deps = [ "users" ];
    text = "${seed-user-configs}";
  };
}
