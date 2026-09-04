# nix-my-gnome (`nmg`)

Convert a live `dconf` database — or a saved `dconf dump` file — into a
[home-manager](https://github.com/nix-community/home-manager) compatible
`dconf.settings` Nix module.

GNOME (and every app that stores its state in dconf — Nautilus, Evolution,
virt-manager, GNOME Shell extensions, GTK file choosers, etc.) keeps its
settings in a binary database. `nmg` reads dconf's plain-text dump format
and emits a `dconf.settings` attrset with correctly typed values
(`lib.hm.gvariant.mkUint32`, `mkTuple`, `mkVariant`, ...), ready to drop
into your home-manager configuration.

## Install

### With the flake

```console
$ nix run github:stefan-hacks/nix-my-gnome -- --help
```

or add it to your flake inputs and reference `packages.${system}.nmg`.

### With pip

```console
$ pip install --user .
$ nmg --help
```

Requires Python 3.10+. No runtime dependencies outside the standard
library.

## Usage

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

Import the result into your home-manager config:

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

## What gets generated

Every dconf section becomes a `dconf.settings."path/to/section"` attrset.
Typed GVariant values are preserved using home-manager's `lib.hm.gvariant`
helpers so round-tripping is faithful:

```ini
[org/gnome/desktop/interface]
clock-format='12h'
scaling-factor=uint32 1
```

becomes

```nix
"org/gnome/desktop/interface" = {
  clock-format = "12h";
  scaling-factor = (lib.hm.gvariant.mkUint32 1);
};
```

Nested tuples, arrays, dicts, and variants (as seen in things like GNOME
Weather's location cache or Shell's `app-picker-layout`) are parsed
recursively. These are exactly the kind of values that are cheap to
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
