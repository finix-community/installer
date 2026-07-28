# Sample of a generated Finix target system

These three files are a representative sample of exactly what
`calamares-finix-extensions/src/modules/nixos/main.py` writes to `/etc/finix/` on the
target during a Finix install:

- `flake.nix` — verbatim from main.py's `cfgflake` (finix + nixpkgs inputs, `finixSystem`).
- `configuration.nix` — assembled from main.py's templates (Finix service stack, limine
  bootloader, hostname/timezone/locale/console/user substitutions).
- `hardware-configuration.nix` — a minimal example (real installs get this from
  `nixos-generate-config`).

It is used as a fixture by `tests/render_and_eval.py`, and can also be checked on its
own — `nix eval .#nixosConfigurations.finixos.config.system.build.toplevel.drvPath`
evaluates cleanly to a `finix-system.drv` against `github:finix-community/finix`:

```bash
cd reference/finix-target-sample && git init -q && git add -A
nix eval .#nixosConfigurations.finixos.config.system.build.toplevel.drvPath
```

Note that evaluation only shows the configuration is *valid*, not that it *boots or
installs*: device paths, UEFI/Limine and dual-boot entries have to be checked on real
hardware.
