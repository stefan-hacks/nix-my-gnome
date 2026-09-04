from nmg.categorize import categorize
from nmg.emit import render_single, render_split
from nmg.parser import parse_dconf_ini

SAMPLE = """
[org/gnome/desktop/interface]
clock-format='12h'

[org/gnome/shell/extensions/dash-to-dock]
dock-position='BOTTOM'

[org/virt-manager/virt-manager]
manager-window-height=550

[org/gnome/evolution]
version='3.60.2'
"""


def test_categorize_known_prefixes():
    assert categorize("org/gnome/shell/extensions/dash-to-dock") == "shell-extensions"
    assert categorize("org/gnome/shell") == "shell"
    assert categorize("org/virt-manager/virt-manager") == "virt-manager"
    assert categorize("org/gnome/evolution") == "evolution"
    assert categorize("org/gtk/settings/file-chooser") == "gtk"


def test_categorize_default_bucket():
    assert categorize("com/example/totally-unknown-app") == "misc"


def test_render_single_contains_all_sections():
    doc = parse_dconf_ini(SAMPLE)
    out = render_single(doc)
    assert '"org/gnome/desktop/interface"' in out
    assert '"org/virt-manager/virt-manager"' in out
    assert "dconf.settings" in out
    assert "{ lib, ... }:" in out


def test_render_single_no_header():
    doc = parse_dconf_ini(SAMPLE)
    out = render_single(doc, module_header=False)
    assert "{ lib, ... }:" not in out
    assert out.strip().startswith("{")


def test_render_split_groups_by_category():
    doc = parse_dconf_ini(SAMPLE)
    files = render_split(doc)
    assert "shell-extensions.nix" in files
    assert "virt-manager.nix" in files
    assert "evolution.nix" in files
    assert "gtk.nix" in files
    assert "default.nix" in files
    assert "./gtk.nix" in files["default.nix"]
    assert "./virt-manager.nix" in files["default.nix"]
