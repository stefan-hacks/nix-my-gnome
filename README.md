<div align="center">

<img src="https://raw.githubusercontent.com/NixOS/nixos-artwork/master/logo/nix-snowflake.svg" width="120" alt="NixOS logo" />

# nix-my-gnome

**`nmg`** — turn a `dconf` database into a home-manager `dconf.settings` module.

[![CI](https://github.com/stefan-hacks/nix-my-gnome/actions/workflows/ci.yml/badge.svg)](https://github.com/stefan-hacks/nix-my-gnome/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Nix Flake](https://img.shields.io/badge/Nix-Flake-5277C3?logo=nixos&logoColor=white)](flake.nix)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

*Stop hand-writing `dconf.settings`. Dump your GNOME, keep your GNOME.*

</div>

---

## What is this?

GNOME — and every app that stores its state in dconf (Nautilus, Evolution,
virt-manager, Shell extensions, GTK file choosers...) — keeps its settings
in a binary database, not a config file. **`nmg`** reads dconf's plain-text
dump and turns it into a properly typed
[home-manager](https://github.com/nix-community/home-manager)
`dconf.settings` module: your entire desktop, declared.

```ini
[org/gnome/desktop/interface]
clock-format='12h'
scaling-factor=uint32 1
```

```nix
"org/gnome/desktop/interface" = {
  clock-format = "12h";
  scaling-factor = (lib.hm.gvariant.mkUint32 1);
};
```

No more manually chasing `lib.hm.gvariant.mkUint32` / `mkTuple` / `mkVariant`
for every setting GNOME decided to remember for you.

## Features

| | |
|---|---|
| 🪄 **Faithful GVariant typing** | Correctly emits `mkUint32`, `mkUint64`, `mkInt64`, `mkTuple`, `mkVariant` — nested arbitrarily deep. |
| 🔌 **Pipe-friendly** | `dconf dump / \| nmg -o home.nix` — no intermediate files required. |
| 💾 **Or use a saved dump** | `nmg -i dconf.ini -o home.nix` for a dump you already have lying around. |
| 🧩 **Single-file or split** | One module, or `-s`/`--split` into logical per-app files (Shell extensions, GTK, Evolution, virt-manager, Nautilus, ...). |
| 📦 **Zero runtime deps** | Pure Python standard library. Packaged as a Nix flake app. |
| ✅ **Tested** | Parser + emitter covered by pytest, run in CI on 3.10–3.12. |

## Quickstart

```console
$ dconf dump / | nix run github:stefan-hacks/nix-my-gnome -- -o home.nix
```

That's it — `home.nix` now contains your entire dconf database as a
home-manager module. Import it and rebuild.

## Using it in your flake

You don't need to install `nmg` permanently — it's a code generator you run
once (or whenever you want to refresh your settings), and commit the
*output* to your NixOS/home-manager config. But wiring it into your flake
gets you a reproducible, always-available copy of the tool.

### 1. Add the input

```nix
# flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    home-manager.url = "github:nix-community/home-manager/release-26.05";

    nix-my-gnome.url = "github:stefan-hacks/nix-my-gnome";
    # keep it locked to your nixpkgs to avoid pulling a second copy:
    nix-my-gnome.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, home-manager, nix-my-gnome, ... }@inputs:
    let
      system = "x86_64-linux";
    in
    {
      nixosConfigurations.my-host = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          ./configuration.nix
          home-manager.nixosModules.home-manager
          {
            home-manager.users.stefan = import ./home.nix;
            # make `nmg` available inside the user's environment
            home-manager.users.stefan.home.packages = [
              nix-my-gnome.packages.${system}.default
            ];
          }
        ];
      };
    };
}
```

### 2. Run it whenever you want to refresh your settings

```console
$ dconf dump / | nmg -s -o ~/nixos-config/home/gnome
```

### 3. Import the generated module

```nix
# home.nix
{ ... }:
{
  imports = [
    ./gnome                     # if you used -s/--split
    # or: ./gnome-settings.nix  # single-file mode
  ];
}
```

### 4. Rebuild

```console
$ sudo nixos-rebuild switch --flake .#my-host
```

Your GNOME desktop is now declared in your flake, right alongside
everything else.

> [!TIP]
> `nix-my-gnome` is a **generator**, not a running service — you don't need
> to keep it in `home.packages` long-term. Running it once via
> `nix run github:stefan-hacks/nix-my-gnome` (no input pinning required) is
> just as valid; add it to your flake inputs only if you want it available
> offline / version-pinned / in your dev shell.

### As a one-off, without touching your flake at all

```console
$ nix run github:stefan-hacks/nix-my-gnome -- -i dconf.ini -o home.nix
```

### In a dev shell

```console
$ nix shell github:stefan-hacks/nix-my-gnome
$ nmg --help
```

## Usage reference

### Pipe your live dconf database straight in

```console
$ dconf dump / | nmg -o home.nix
```

### Use an already-saved dump

```console
$ dconf dump / > dconf.ini
$ nmg -i dconf.ini -o home.nix
```

### Print to stdout instead of writing a file

```console
$ nmg -i dconf.ini
```
(omit `-o`, or pass `-o -`)

### Split into logical per-app files

```console
$ nmg -i dconf.ini -s -o ./gnome-settings
nmg: wrote 18 files to ./gnome-settings/
  ./gnome-settings/shell-extensions.nix
  ./gnome-settings/shell.nix
  ./gnome-settings/gtk.nix
  ./gnome-settings/evolution.nix
  ./gnome-settings/virt-manager.nix
  ./gnome-settings/nautilus.nix
  ...
  ./gnome-settings/default.nix
```

`-s`/`--split` groups sections by app/subsystem (GNOME Shell extensions,
GTK & file chooser, Evolution, virt-manager, Nautilus, notifications,
window manager, input devices, media apps, etc. — see
[`nmg/categorize.py`](nmg/categorize.py) for the full rule list) and
writes one file per group, plus a `default.nix` that imports all of them.
Anything that doesn't match a known rule lands in `misc.nix`.

```nix
{
  imports = [ ./gnome-settings ];   # or ./home.nix for single-file mode
}
```

### CLI reference

```
usage: nmg [-h] [-i FILE] [-o PATH] [-s] [--no-header] [--version]

  -i, --input FILE    Read a saved dconf dump from FILE instead of stdin.
  -o, --output PATH   File path (single-file mode) or directory (-s mode).
                       Defaults to stdout / ./nmg-out respectively.
  -s, --split          Split output into logical per-app files.
  --no-header          Omit the comment header and `{ lib, ... }:` function
                       head in single-file mode (useful when splicing the
                       attrset into an existing module by hand).
```

## Other install methods

<details>
<summary>pip</summary>

```console
$ pip install --user .
$ nmg --help
```

Requires Python 3.10+. No runtime dependencies outside the standard
library.
</details>

## What gets generated

Every dconf section becomes a `dconf.settings."path/to/section"` attrset.
Typed GVariant values are preserved using home-manager's `lib.hm.gvariant`
helpers, including negative numbers, nested tuples, arrays, dicts, and
variants (as seen in GNOME Weather's location cache or Shell's
`app-picker-layout`) — parsed recursively so round-tripping is faithful.

These deeply nested fields are exactly the kind of state that's cheap to
regenerate from the GUI and easy to get subtly wrong by hand — after
applying, it's worth spot-checking anything genuinely load-bearing with
`dconf read /some/path`.

## Development

```console
$ nix develop        # or: pip install -e '.[dev]' pytest
$ pytest
```

## License

MIT — see [LICENSE](LICENSE).
