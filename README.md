<div align="center">

<!-- NixOS Snowflake Logo -->
<img src="https://raw.githubusercontent.com/NixOS/nixos-artwork/master/logo/nix-snowflake.svg" width="140" alt="NixOS Snowflake Logo" />

<!-- Project Title -->
<h1 align="center">nix-my-gnome</h1>

<!-- Tagline -->
<p align="center"><strong>Turn your GNOME dconf dump into a declarative Home Manager module.</strong></p>

<!-- Badges -->
<p align="center">
  <a href="https://github.com/stefan-hacks/nix-my-gnome/actions/workflows/ci.yml">
    <img src="https://github.com/stefan-hacks/nix-my-gnome/actions/workflows/ci.yml/badge.svg" alt="CI" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" />
  </a>
  <a href="flake.nix">
    <img src="https://img.shields.io/badge/Nix-Flake-5277C3?logo=nixos&logoColor=white" alt="Nix Flake" />
  </a>
  <a href="pyproject.toml">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  </a>
</p>

<!-- Divider -->
<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" alt="divider" />

</div>

## ✨ What is this?

GNOME stores its settings in a binary dconf database — not a config file you can version.
**`nmg`** reads a dconf dump and generates a properly typed
[Home Manager](https://github.com/nix-community/home-manager) `dconf.settings`
module. Your entire desktop, declared.

| dconf dump | Generated Nix |
|---|---|
| <pre>[org/gnome/desktop/interface]<br>clock-format='12h'<br>scaling-factor=uint32 1</pre> | <pre>"org/gnome/desktop/interface" = {<br>&nbsp;&nbsp;clock-format = "12h";<br>&nbsp;&nbsp;scaling-factor = lib.hm.gvariant.mkUint32 1;<br>};</pre> |

No more hand-writing `mkUint32`, `mkTuple`, or `mkVariant` for every setting
GNOME decided to persist.

## 🚀 Quickstart

Generate your settings straight from your live dconf database:

```console
$ dconf dump / | nix run github:stefan-hacks/nix-my-gnome -- -o home.nix
```

Or from a saved dump file:

```console
$ nix run github:stefan-hacks/nix-my-gnome -- -i dconf.ini -o home.nix
```

That's it. Import `home.nix` into your Home Manager config and rebuild.

## 🛠️ Using it in your flake

You don't need to install `nmg` permanently — it's a code generator you run
once (or whenever you want to refresh settings), and commit the *output* to
your NixOS config. Wiring it into your flake makes it reproducible and
offline-capable.

### 1. Add the input

```nix
# flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    home-manager.url = "github:nix-community/home-manager/release-26.05";

    nix-my-gnome.url = "github:stefan-hacks/nix-my-gnome";
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
            home-manager.users.stefan.home.packages = [
              nix-my-gnome.packages.${system}.default
            ];
          }
        ];
      };
    };
}
```

### 2. Regenerate your GNOME settings

```console
$ dconf dump / | nmg -s -o ~/nixos-config/home/stefan-hacks/gnome
nmg: wrote 18 files to ~/nixos-config/home/stefan-hacks/gnome/
```

### 3. Import the generated module

```nix
# home.nix
{ ... }:
{
  imports = [
    ./gnome    # generated with -s/--split
  ];
}
```

### 4. Rebuild

```console
$ sudo nixos-rebuild switch --flake .#my-host
```

> [!TIP]
> `nix-my-gnome` is a **generator**, not a service. You don't need it in
> `home.packages` long-term. Run it once with
> `nix run github:stefan-hacks/nix-my-gnome` (no input pinning required)
> and commit the output.

## 📋 Features

| | |
|---|---|
| 🪄 **Faithful GVariant typing** | Emits `mkUint32`, `mkUint64`, `mkInt64`, `mkTuple`, `mkVariant`, `mkDictionaryEntry` — nested arbitrarily deep. |
| 🔌 **Pipe-friendly** | `dconf dump / \| nmg -o home.nix` — no intermediate files required. |
| 📁 **Single-file or split** | One module, or `-s`/`--split` into logical per-app files (Shell, GTK, Evolution, Nautilus, ...). |
| 📦 **Zero runtime deps** | Pure Python standard library. Packaged as a Nix flake app. |
| ✅ **Tested** | Parser + emitter covered by pytest, run in CI on 3.10–3.12. |

## 📖 Usage reference

### Pipe your live dconf database

```console
$ dconf dump / | nmg -o home.nix
```

### Use a saved dump file

```console
$ dconf dump / > dconf.ini
$ nmg -i dconf.ini -o home.nix
```

### Print to stdout

```console
$ nmg -i dconf.ini
```
(Omit `-o`, or pass `-o -`)

### Split into per-app files

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

`-s`/`--split` groups sections by app/subsystem and writes one file per group,
plus a `default.nix` that imports all of them. Anything that doesn't match a
known rule lands in `misc.nix`. See [`nmg/categorize.py`](nmg/categorize.py)
for the full rule list.

### CLI reference

```
usage: nmg [-h] [-i FILE] [-o PATH] [-s] [--no-header] [--version]

  -i, --input FILE    Read a saved dconf dump from FILE instead of stdin.
  -o, --output PATH   File path (single-file mode) or directory (-s mode).
                       Defaults to stdout / ./nmg-out respectively.
  -s, --split          Split output into logical per-app files.
  --no-header          Omit the comment header and `{ lib, ... }:` function
                       head in single-file mode.
```

## 🧩 Other install methods

<details>
<summary><strong>pip</strong></summary>

```console
$ pip install --user .
$ nmg --help
```

Requires Python 3.10+. No runtime dependencies outside the standard library.

</details>

## 🔍 What gets generated

Every dconf section becomes a `dconf.settings."path/to/section"` attrset.
Typed GVariant values are preserved using Home Manager's `lib.hm.gvariant`
helpers, including negative numbers, nested tuples, arrays, dicts, and
variants — as seen in GNOME Weather's location cache or Shell's
`app-picker-layout`. Parsed recursively so round-tripping is faithful.

These deeply nested fields are exactly the kind of state that's cheap to
regenerate from the GUI and easy to get subtly wrong by hand — after
applying, it's worth spot-checking anything genuinely load-bearing with
`dconf read /some/path`.

## 🧪 Development

```console
$ nix develop        # or: pip install -e '.[dev]' pytest
$ pytest
```

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

<p><sub>Made with ❄️ for the Nix community</sub></p>

</div>
