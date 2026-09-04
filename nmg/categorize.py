"""
Rules for grouping dconf section paths into logical, per-app Nix files
when splitting output with `nmg -s`.

Rules are checked in order; the first matching prefix wins. Anything that
doesn't match falls into the "misc" bucket.
"""

from __future__ import annotations

# (path_prefix, output_filename_stem, human description)
RULES: list[tuple[str, str, str]] = [
    ("org/gnome/shell/extensions/", "shell-extensions", "GNOME Shell extension settings"),
    ("org/gnome/shell/", "shell", "GNOME Shell (keybindings, weather, favorites, world clocks)"),
    ("org/gnome/mutter/", "mutter", "Mutter window manager"),
    ("org/gnome/desktop/wm/", "window-manager", "Window manager keybindings/preferences"),
    ("org/gnome/desktop/notifications/", "notifications", "Notifications"),
    ("org/gnome/desktop/a11y/", "accessibility", "Accessibility"),
    ("org/gnome/desktop/peripherals/", "input-devices", "Mouse/touchpad/pointing-stick"),
    ("org/gnome/desktop/input-sources", "input-devices", "Keyboard input sources"),
    ("org/gnome/desktop/interface", "gtk", "GTK / desktop interface theme and fonts"),
    ("org/gnome/desktop/background", "gtk", "Desktop wallpaper"),
    ("org/gnome/desktop/sound", "gtk", "Desktop sound theme"),
    ("org/gnome/desktop/session", "gtk", "Desktop session (idle delay etc.)"),
    ("org/gnome/desktop/app-folders", "app-folders", "App-grid folders"),
    ("desktop/ibus/", "input-devices", "IBus input method"),
    ("org/gtk/", "gtk", "GTK file chooser / color chooser"),
    ("org/gnome/nautilus/", "nautilus", "Files (Nautilus)"),
    ("org/gnome/evolution", "evolution", "Evolution mail/calendar/contacts"),
    ("org/gnome/Contacts", "evolution", "GNOME Contacts"),
    ("org/freedesktop/folks", "evolution", "Contacts backend (folks)"),
    ("org/virt-manager/", "virt-manager", "virt-manager / libvirt VM manager"),
    ("org/gnome/settings-daemon/", "settings-daemon", "GNOME Settings Daemon plugins"),
    ("org/gnome/control-center", "settings-daemon", "GNOME Settings app state"),
    ("org/gnome/portal/", "settings-daemon", "xdg-desktop-portal file chooser history"),
    ("org/gnome/clocks", "media", "GNOME Clocks"),
    ("org/gnome/Weather", "media", "GNOME Weather"),
    ("org/gnome/GWeather4", "media", "GWeather"),
    ("org/gnome/Music", "media", "GNOME Music"),
    ("de/haeckerfelix/Shortwave", "media", "Shortwave internet radio"),
    ("org/gnome/Showtime", "media", "Showtime video player"),
    ("org/soundconverter", "media", "SoundConverter"),
    ("org/nickvision/", "media", "Nickvision apps (tube converter etc.)"),
    ("net/nokyan/Resources", "system-monitor", "Resources system monitor"),
    ("org/gnome/GPaste", "misc-apps", "GPaste clipboard manager"),
    ("org/gnome/TextEditor", "misc-apps", "GNOME Text Editor"),
    ("org/gnome/eog/", "misc-apps", "Eye of GNOME image viewer"),
    ("org/gnome/papers", "misc-apps", "Papers (document viewer)"),
    ("org/gnome/tweaks", "misc-apps", "GNOME Tweaks"),
    ("io/gitlab/adhami3310/Impression", "misc-apps", "Impression (ISO writer)"),
]

DEFAULT_STEM = "misc"


def categorize(section_path: str) -> str:
    for prefix, stem, _desc in RULES:
        if section_path == prefix.rstrip("/") or section_path.startswith(prefix):
            return stem
    return DEFAULT_STEM
