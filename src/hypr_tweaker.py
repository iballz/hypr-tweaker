#!/usr/bin/env python3
"""
Hypr Tweaker - Live Visual Settings Configurator for Hyprland
A modern, polished Libadwaita / GTK4 GUI for configuring Hyprland.
Features real-time live preview via hyprctl, modular variable sync, and persistent saving.
"""

import sys
import os
import json
import subprocess
import re
import threading

# Dynamic directory resolution
APP_DIR = os.path.dirname(os.path.realpath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

for share_candidate in [
    os.path.expanduser("~/.local/share/hypr-tweaker"),
    "/usr/share/hypr-tweaker",
    "/usr/local/share/hypr-tweaker"
]:
    if os.path.isdir(share_candidate) and share_candidate not in sys.path:
        sys.path.append(share_candidate)

try:
    import psr_helper
except ImportError:
    try:
        import caelestia_psr_helper as psr_helper
    except ImportError:
        psr_helper = None

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango, Gdk, Gio

APP_ID = "io.github.iballz.hyprtweaker"
CAELESTIA_CONF_DIR = os.path.expanduser("~/.config/caelestia")
HYPR_CONF_DIR = os.path.expanduser("~/.config/hypr")
VARS_LUA = os.path.join(CAELESTIA_CONF_DIR, "hypr-vars.lua")
HYPR_TWEAKER_CONF = os.path.join(HYPR_CONF_DIR, "hypr-tweaker.conf")
DEFAULT_VARS_LUA = os.path.join(HYPR_CONF_DIR, "variables.lua")
SCHEME_LUA = os.path.join(HYPR_CONF_DIR, "scheme", "current.lua")

CUSTOM_CSS = b"""
/* Modern editable slider numeric box */
.slider-entry {
    min-width: 52px;
    min-height: 28px;
    padding: 1px 6px;
    border-radius: 8px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Adwaita Mono', monospace;
    font-weight: 600;
    font-size: 0.85rem;
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: #ffffff;
    transition: all 180ms cubic-bezier(0.25, 1, 0.5, 1);
}
.slider-entry:focus-within, .slider-entry:focus {
    border-color: rgba(255, 255, 255, 0.40);
    background-color: rgba(255, 255, 255, 0.10);
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.15);
    color: #ffffff;
}
.slider-unit-badge {
    font-size: 0.80rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.65);
    min-width: 18px;
}

/* Polished modern switches */
switch {
    border-radius: 9999px;
    outline: none;
    transition: all 200ms cubic-bezier(0.25, 1, 0.5, 1);
}
switch:checked {
    background-color: #5b5478;
    border: 1px solid #7c739e;
}
switch:checked > slider {
    background-color: #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}
switch:not(:checked) {
    background-color: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.14);
}
switch:not(:checked) > slider {
    background-color: #9a96a0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}
switch:hover:checked {
    background-color: #69618a;
    border-color: #8c82b2;
}
switch:hover:not(:checked) {
    background-color: rgba(255, 255, 255, 0.14);
}

/* Palette swatches */
.color-swatch-pair {
    border-radius: 9999px;
    padding: 4px 6px;
    background-color: alpha(@card_fg_color, 0.07);
    border: 1px solid alpha(@card_fg_color, 0.12);
}
.swatch-dot {
    border-radius: 9999px;
    min-width: 16px;
    min-height: 16px;
    border: 1px solid alpha(white, 0.25);
}

.swatch-caelestia-act { background-color: #c6c6c6; }
.swatch-caelestia-inact { background-color: #262626; }
.swatch-cyan-act { background-color: #80f0e7; }
.swatch-cyan-inact { background-color: #102025; }
.swatch-catppuccin-act { background-color: #cba6f7; }
.swatch-catppuccin-inact { background-color: #313244; }
.swatch-nord-act { background-color: #88c0d0; }
.swatch-nord-inact { background-color: #2e3440; }
.swatch-tokyo-act { background-color: #7aa2f7; }
.swatch-tokyo-inact { background-color: #1a1b26; }
.swatch-gruvbox-act { background-color: #fabd2f; }
.swatch-gruvbox-inact { background-color: #3c3836; }
"""

def get_installed_cursor_themes():
    themes = set()
    for search_dir in ["/usr/share/icons", os.path.expanduser("~/.icons"), os.path.expanduser("~/.local/share/icons")]:
        if os.path.isdir(search_dir):
            try:
                for name in os.listdir(search_dir):
                    if os.path.isdir(os.path.join(search_dir, name, "cursors")):
                        themes.add(name)
            except Exception:
                pass
    return sorted(list(themes)) or ["Adwaita"]

def get_gsettings_font(key):
    try:
        res = subprocess.check_output(["gsettings", "get", "org.gnome.desktop.interface", key], text=True).strip()
        if res.startswith("'") and res.endswith("'"):
            return res[1:-1]
        return res
    except Exception:
        return "Sans 11"

def set_gsettings(key, value, is_string=True):
    try:
        val_arg = f"'{value}'" if is_string else str(value)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", key, val_arg], check=False)
    except Exception:
        pass

def update_gtk_settings_ini(key, value):
    for path in [
        os.path.expanduser("~/.config/gtk-3.0/settings.ini"),
        os.path.expanduser("~/.config/gtk-4.0/settings.ini")
    ]:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    lines = f.readlines()
                new_lines = []
                found = False
                for line in lines:
                    if line.strip().startswith(f"{key}="):
                        new_lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"{key}={value}\n")
                with open(path, "w") as f:
                    f.writelines(new_lines)
            except Exception:
                pass

def update_foot_font(font_desc_str):
    foot_path = os.path.expanduser("~/.config/foot/foot.ini")
    if not os.path.exists(foot_path):
        return
    try:
        match = re.search(r"^(.*?)\s+([0-9]+(?:\.[0-9]+)?)$", font_desc_str.strip())
        if match:
            family = match.group(1)
            size = match.group(2)
        else:
            family = font_desc_str.strip()
            size = "12"

        if "terminus" in family.lower():
            font_entry = f"{family}:size={size}, JetBrains Mono Nerd Font:size=12"
        else:
            font_entry = f"{family}:size={size}"

        with open(foot_path, "r") as f:
            lines = f.readlines()
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith("font="):
                new_lines.append(f"font={font_entry}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.insert(2, f"font={font_entry}\n")
        with open(foot_path, "w") as f:
            f.writelines(new_lines)
    except Exception:
        pass

def update_default_cursor_theme(theme_name):
    path = os.path.expanduser("~/.icons/default/index.theme")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = f"[Icon Theme]\nName=Default\nComment=Default Cursor Theme\nInherits={theme_name}\n"
        with open(path, "w") as f:
            f.write(content)
    except Exception:
        pass

def update_shell_step_live(service, step_int):
    try:
        subprocess.Popen(
            ["qs", "-c", "caelestia", "ipc", "call", service, "setStep", str(int(step_int))],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def load_caelestia_scheme_colors():
    colors = {
        "primary": "c6c6c6",
        "inversePrimary": "5f5f5f",
        "onSurfaceVariant": "ababab",
        "background": "0e0e0e"
    }
    if os.path.isfile(SCHEME_LUA):
        try:
            with open(SCHEME_LUA, "r") as f:
                content = f.read()
                for key in colors.keys():
                    match = re.search(rf'{key}\s*=\s*"([0-9a-fA-F]+)"', content)
                    if match:
                        colors[key] = match.group(1)
        except Exception:
            pass
    return colors

def detect_gpus_info():
    info = {"igpu": None, "dgpu": None}
    try:
        lspci = subprocess.check_output(["lspci"], text=True)
        for line in lspci.splitlines():
            if any(k in line for k in ["VGA compatible controller", "3D controller", "Display controller"]):
                parts = line.split(": ", 1)
                name = parts[1] if len(parts) > 1 else line
                name = re.sub(r"\(rev [0-9a-fA-F]+\)", "", name).strip()
                if "Intel" in name or "AMD" in name:
                    if not info["igpu"]:
                        info["igpu"] = name
                    elif not info["dgpu"]:
                        info["dgpu"] = name
                elif "NVIDIA" in name:
                    info["dgpu"] = name
                else:
                    if not info["igpu"]:
                        info["igpu"] = name
                    else:
                        info["dgpu"] = name
    except Exception:
        pass

    if not info["igpu"] and not info["dgpu"]:
        for i in range(6):
            vendor_path = f"/sys/class/drm/card{i}/device/vendor"
            if os.path.exists(vendor_path):
                try:
                    with open(vendor_path, "r") as f:
                        v = f.read().strip().lower()
                    if v == "0x10de":
                        info["dgpu"] = f"NVIDIA Graphics (/dev/dri/card{i})"
                    elif v == "0x8086":
                        info["igpu"] = f"Intel Graphics (/dev/dri/card{i})"
                    elif v == "0x1002":
                        info["igpu"] = f"AMD Radeon Graphics (/dev/dri/card{i})"
                except Exception:
                    pass
    return info

def get_current_hyprland_gpu():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    hypr_dir = os.path.join(runtime_dir, "hypr")
    if os.path.isdir(hypr_dir):
        try:
            for sub in os.listdir(hypr_dir):
                log_file = os.path.join(hypr_dir, sub, "hyprland.log")
                if os.path.isfile(log_file):
                    with open(log_file, "r") as f:
                        for line in f:
                            if "CDRMRenderer(drm): Using device" in line:
                                dev = line.strip().split("Using device")[-1].strip()
                                card_match = re.search(r"card\d+", dev)
                                if card_match:
                                    v_path = f"/sys/class/drm/{card_match.group(0)}/device/vendor"
                                    if os.path.isfile(v_path):
                                        try:
                                            with open(v_path, "r") as vf:
                                                vend = vf.read().strip().lower()
                                            if vend == "0x10de":
                                                return f"NVIDIA Dedicated GPU ({dev})"
                                            elif vend == "0x8086":
                                                return f"Intel Integrated GPU ({dev})"
                                            elif vend == "0x1002":
                                                return f"AMD Integrated GPU ({dev})"
                                        except Exception:
                                            pass
                                return dev
        except Exception:
            pass
    return "Integrated GPU (Default)"

def get_hyprland_option(option_name):
    try:
        out = subprocess.check_output(["hyprctl", "getoption", option_name, "-j"], text=True, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        if "int" in data:
            return data["int"]
        elif "float" in data:
            return data["float"]
        elif "bool" in data:
            return data["bool"]
        elif "str" in data:
            return data["str"]
        elif "css" in data:
            parts = data["css"].strip().split()
            if parts:
                return int(parts[0])
    except Exception:
        pass
    return None

def format_hypr_color(c, default="rgba(c6c6c688)"):
    if not c:
        return default
    c = str(c).strip()
    if c.startswith("rgba(") or c.startswith("rgb("):
        return c
    clean = c.replace("#", "")
    if len(clean) == 6:
        return f"rgb({clean})"
    elif len(clean) == 8:
        return f"rgba({clean})"
    return default

def extract_configs_via_lua():
    """Extract merged configuration table from variables.lua and hypr-vars.lua via lua CLI"""
    lua_code = """
local home = os.getenv("HOME")
package.path = package.path .. ";" .. home .. "/.config/hypr/?.lua;" .. home .. "/.config/caelestia/?.lua"
local defaults = require("variables")
local ok, overrides = pcall(require, "hypr-vars")
if not ok or type(overrides) ~= "table" then overrides = {} end

local merged = {}
for k, v in pairs(defaults) do
    if type(v) ~= "table" then merged[k] = v end
end
for k, v in pairs(overrides) do
    if type(v) ~= "table" then merged[k] = v end
end

local function escape(s)
    return s:gsub("\\\\", "\\\\\\\\"):gsub("\\"", "\\\\\\""):gsub("\\n", "\\\\n")
end

local parts = {}
for k, v in pairs(merged) do
    local val_str
    if type(v) == "boolean" then
        val_str = v and "true" or "false"
    elseif type(v) == "number" then
        val_str = tostring(v)
    elseif type(v) == "string" then
        val_str = "\\"" .. escape(v) .. "\\""
    end
    if val_str then
        table.insert(parts, string.format("\\"%s\\": %s", k, val_str))
    end
end
print("{" .. table.concat(parts, ", ") .. "}")
"""
    try:
        out = subprocess.check_output(["lua", "-e", lua_code], text=True, stderr=subprocess.DEVNULL).strip()
        return json.loads(out)
    except Exception:
        return {}


class SliderRow(Adw.ActionRow):
    """
    Modern slider row featuring:
    - Smooth Gtk.Scale
    - Directly editable, styled numeric input box (Gtk.Entry)
    - Optional unit indicator (px, %, etc.)
    - Real-time debounced live updating
    """
    def __init__(self, title, subtitle, min_val, max_val, step, current_val, unit="", digits=0, on_change=None):
        super().__init__(title=title, subtitle=subtitle)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.digits = digits
        self.unit = unit
        self.on_change = on_change
        self._updating = False

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)

        # Slider scale
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, step)
        self.scale.set_value(float(current_val))
        self.scale.set_size_request(200, -1)
        self.scale.set_hexpand(True)
        self.scale.set_valign(Gtk.Align.CENTER)

        # Editable numeric entry box
        self.entry = Gtk.Entry()
        self.entry.set_alignment(0.5)
        self.entry.set_width_chars(6)
        self.entry.set_max_width_chars(8)
        self.entry.set_valign(Gtk.Align.CENTER)
        self.entry.add_css_class("slider-entry")
        self._set_entry_text(current_val)

        # Connect signals
        self.scale.connect("value-changed", self._on_scale_changed)
        self.entry.connect("activate", self._on_entry_submitted)

        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("enter", lambda c: self.entry.select_region(0, -1))
        focus_ctrl.connect("leave", self._on_entry_submitted)
        self.entry.add_controller(focus_ctrl)

        box.append(self.scale)
        box.append(self.entry)

        # Unit badge if unit exists
        if unit:
            self.lbl_unit = Gtk.Label(label=unit)
            self.lbl_unit.add_css_class("slider-unit-badge")
            self.lbl_unit.set_valign(Gtk.Align.CENTER)
            box.append(self.lbl_unit)

        self.add_suffix(box)

    def _set_entry_text(self, val):
        if self.digits == 0:
            self.entry.set_text(str(int(round(val))))
        else:
            self.entry.set_text(f"{val:.{self.digits}f}")

    def _on_scale_changed(self, scale):
        if self._updating:
            return
        val = scale.get_value()
        val = int(round(val)) if self.digits == 0 else round(val, self.digits)

        self._updating = True
        self._set_entry_text(val)
        self._updating = False

        if self.on_change:
            self.on_change(val)

    def _on_entry_submitted(self, *args):
        if self._updating:
            return
        txt = self.entry.get_text().strip()
        try:
            val = float(txt)
            val = max(self.min_val, min(self.max_val, val))
            val = int(round(val)) if self.digits == 0 else round(val, self.digits)

            self._updating = True
            self.scale.set_value(val)
            self._set_entry_text(val)
            self._updating = False

            if self.on_change:
                self.on_change(val)
        except ValueError:
            self._set_entry_text(self.scale.get_value())

    def set_val(self, val):
        self._updating = True
        self.scale.set_value(float(val))
        self._set_entry_text(val)
        self._updating = False


def make_switch_row(title, subtitle, active, on_change=None):
    row = Adw.SwitchRow(title=title, subtitle=subtitle, active=bool(active))
    if on_change:
        row.connect("notify::active", lambda r, p: on_change(r.get_active()))
    return row


class ComboRow(Adw.ComboRow):
    def __init__(self, title, subtitle, items, current_item, on_change=None):
        super().__init__(title=title, subtitle=subtitle)
        self.items = items
        self.on_change = on_change
        model = Gtk.StringList.new(items)
        self.set_model(model)
        if current_item in items:
            self.set_selected(items.index(current_item))
        elif items:
            self.set_selected(0)
        self.connect("notify::selected", self._on_selected)

    def _on_selected(self, row, param):
        idx = self.get_selected()
        if 0 <= idx < len(self.items) and self.on_change:
            self.on_change(self.items[idx])

    def set_selected_item(self, item_name):
        if item_name in self.items:
            self.set_selected(self.items.index(item_name))


class ColorPickerRow(Adw.ActionRow):
    def __init__(self, title, subtitle, current_hex, on_change=None):
        super().__init__(title=title, subtitle=subtitle)
        self.on_change = on_change
        self.dialog = Gtk.ColorDialog()
        self.btn = Gtk.ColorDialogButton(dialog=self.dialog)
        
        rgba = self.parse_color_to_rgba(current_hex)
        self.btn.set_rgba(rgba)
        self.btn.connect("notify::rgba", self._on_rgba_changed)
        self.add_suffix(self.btn)

    def parse_color_to_rgba(self, col_str):
        rgba = Gdk.RGBA()
        if not col_str:
            rgba.parse("rgba(198,198,198,0.9)")
            return rgba
        hex_match = re.search(r'([0-9a-fA-F]{6,8})', str(col_str))
        if hex_match:
            h = hex_match.group(1)
            r = int(h[0:2], 16) / 255.0
            g = int(h[2:4], 16) / 255.0
            b = int(h[4:6], 16) / 255.0
            a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
            rgba.red, rgba.green, rgba.blue, rgba.alpha = r, g, b, a
            return rgba
        try:
            rgba.parse(str(col_str))
        except Exception:
            rgba.parse("rgba(198,198,198,0.9)")
        return rgba

    def set_color(self, col_str):
        rgba = self.parse_color_to_rgba(col_str)
        self.btn.set_rgba(rgba)

    def _on_rgba_changed(self, btn, param):
        rgba = btn.get_rgba()
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        a = int(rgba.alpha * 255)
        hex_str = f"rgba({r:02x}{g:02x}{b:02x}{a:02x})"
        if self.on_change:
            self.on_change(hex_str)


def make_swatch_pair(act_class, inact_class):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    box.add_css_class("color-swatch-pair")
    box.set_valign(Gtk.Align.CENTER)

    dot1 = Gtk.Box()
    dot1.add_css_class("swatch-dot")
    dot1.add_css_class(act_class)

    dot2 = Gtk.Box()
    dot2.add_css_class("swatch-dot")
    dot2.add_css_class(inact_class)

    box.append(dot1)
    box.append(dot2)
    return box


class FontRow(Adw.ActionRow):
    def __init__(self, title, subtitle, current_font_str, on_change=None):
        super().__init__(title=title, subtitle=subtitle)
        self.on_change = on_change
        self.dialog = Gtk.FontDialog()
        self.btn = Gtk.FontDialogButton(dialog=self.dialog)
        if current_font_str:
            desc = Pango.FontDescription.from_string(current_font_str)
            self.btn.set_font_desc(desc)
        self.btn.connect("notify::font-desc", self._on_font_desc_changed)
        self.add_suffix(self.btn)

    def _on_font_desc_changed(self, btn, param):
        desc = btn.get_font_desc()
        if desc and self.on_change:
            self.on_change(desc.to_string())


class TweakerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Hypr Tweaker")
        self.set_default_size(920, 650)

        # Force Dark Mode to match Caelestia aesthetic
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        
        # Load theme CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CUSTOM_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Initial config state
        self.scheme_colors = load_caelestia_scheme_colors()
        self.state = self.load_initial_state()
        self.initial_state = dict(self.state)
        self.apply_timeout_id = None
        self.slider_rows = {}
        border_size = int(self.state.get("windowBorderSize", 1))
        self.last_nonzero_border_size = border_size if border_size > 0 else 1
        self._syncing_border = False

        # Build UI
        self.build_ui()

    def load_initial_state(self):
        loaded = extract_configs_via_lua()
        
        # Merge with defaults
        defaults = {
            "windowGapsIn": 0,
            "windowGapsOut": 0,
            "workspaceGaps": 20,
            "singleWindowGapsOut": 5,
            "windowRounding": 15,
            "windowBorderSize": 1,
            "windowOpacity": 0.95,
            "inactiveOpacity": 0.90,
            "dimInactive": False,
            "dimStrength": 0.15,
            "activeWindowBorderColour": f"rgba({self.scheme_colors['primary']}50)",
            "inactiveWindowBorderColour": f"rgba({self.scheme_colors['onSurfaceVariant']}11)",
            "blurEnabled": True,
            "blurSize": 8,
            "blurPasses": 2,
            "blurXray": False,
            "blurPopups": True,
            "blurInputMethods": True,
            "blurSpecialWs": False,
            "shadowEnabled": True,
            "shadowRange": 15,
            "shadowRenderPower": 4,
            "shadowColour": f"rgba({self.scheme_colors['inversePrimary']}10)",
            "touchpadDisableTyping": True,
            "touchpadScrollFactor": 0.3,
            "touchpadNaturalScroll": True,
            "mouseSensitivity": 0.0,
            "mouseAccelProfile": "flat",
            "gestureFingers": 3,
            "workspaceSwipeFingers": 4,
            "gestureFingersMore": 4,
            "animationsEnabled": True,
            "layout": "dwindle",
            "volumeStep": 5,
            "volumeMax": 100,
            "brightnessStep": 5,
            "cursorTheme": "capitaine-cursors-light",
            "cursorSize": 24,
            "terminal": "foot",
            "browser": "zen-browser",
            "editor": "codium",
            "fileExplorer": "nautilus",
            "audioSettings": "pavucontrol",
            "interfaceFont": get_gsettings_font("font-name"),
            "monospaceFont": get_gsettings_font("monospace-font-name"),
            "primaryGpu": "intel",
        }

        # Fallback to querying active Hyprland options directly if Lua dotfiles are absent
        if not loaded:
            g_in = get_hyprland_option("general:gaps_in")
            if g_in is not None: defaults["windowGapsIn"] = g_in
            g_out = get_hyprland_option("general:gaps_out")
            if g_out is not None: defaults["windowGapsOut"] = g_out
            b_sz = get_hyprland_option("general:border_size")
            if b_sz is not None: defaults["windowBorderSize"] = b_sz
            rnd = get_hyprland_option("decoration:rounding")
            if rnd is not None: defaults["windowRounding"] = rnd
            a_op = get_hyprland_option("decoration:active_opacity")
            if a_op is not None: defaults["windowOpacity"] = a_op
            i_op = get_hyprland_option("decoration:inactive_opacity")
            if i_op is not None: defaults["inactiveOpacity"] = i_op
            d_in = get_hyprland_option("decoration:dim_inactive")
            if d_in is not None: defaults["dimInactive"] = bool(d_in)
            d_st = get_hyprland_option("decoration:dim_strength")
            if d_st is not None: defaults["dimStrength"] = d_st
            bl_en = get_hyprland_option("decoration:blur:enabled")
            if bl_en is not None: defaults["blurEnabled"] = bool(bl_en)
            bl_sz = get_hyprland_option("decoration:blur:size")
            if bl_sz is not None: defaults["blurSize"] = bl_sz
            bl_ps = get_hyprland_option("decoration:blur:passes")
            if bl_ps is not None: defaults["blurPasses"] = bl_ps
            bl_xr = get_hyprland_option("decoration:blur:xray")
            if bl_xr is not None: defaults["blurXray"] = bool(bl_xr)
            bl_po = get_hyprland_option("decoration:blur:popups")
            if bl_po is not None: defaults["blurPopups"] = bool(bl_po)
            bl_sp = get_hyprland_option("decoration:blur:special")
            if bl_sp is not None: defaults["blurSpecialWs"] = bool(bl_sp)
            sh_en = get_hyprland_option("decoration:shadow:enabled")
            if sh_en is not None: defaults["shadowEnabled"] = bool(sh_en)
            sh_rg = get_hyprland_option("decoration:shadow:range")
            if sh_rg is not None: defaults["shadowRange"] = sh_rg
            sh_pw = get_hyprland_option("decoration:shadow:render_power")
            if sh_pw is not None: defaults["shadowRenderPower"] = sh_pw
            m_se = get_hyprland_option("input:sensitivity")
            if m_se is not None: defaults["mouseSensitivity"] = m_se
            m_ac = get_hyprland_option("input:accel_profile")
            if m_ac is not None: defaults["mouseAccelProfile"] = str(m_ac)
            an_en = get_hyprland_option("animations:enabled")
            if an_en is not None: defaults["animationsEnabled"] = bool(an_en)

        for k, v in defaults.items():
            if k not in loaded:
                loaded[k] = v

        # Read shell.json for Caelestia Shell brightnessIncrement / audioIncrement
        shell_json_path = os.path.expanduser("~/.config/caelestia/shell.json")
        if os.path.exists(shell_json_path):
            try:
                with open(shell_json_path, "r") as f:
                    sdata = json.load(f)
                services = sdata.get("services", {})
                if "brightnessIncrement" in services:
                    loaded["brightnessStep"] = int(round(float(services["brightnessIncrement"]) * 100))
                if "audioIncrement" in services:
                    loaded["volumeStep"] = int(round(float(services["audioIncrement"]) * 100))
            except Exception:
                pass

        return loaded

    def build_ui(self):
        # Root Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Toolbar View
        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        # HeaderBar
        header = Adw.HeaderBar()
        
        # Header: Left - Reset button
        reset_content = Adw.ButtonContent(icon_name="edit-undo-symbolic", label="Reset Defaults")
        btn_reset = Gtk.Button(child=reset_content)
        btn_reset.set_tooltip_text("Reset all settings to recommended defaults")
        btn_reset.connect("clicked", self.on_reset_clicked)
        header.pack_start(btn_reset)

        # Header: Middle - Clean Window Title
        title_widget = Adw.WindowTitle(title="Hypr Tweaker", subtitle="Hyprland Visual Settings")
        header.set_title_widget(title_widget)

        # Header: Right - Save and Apply button
        save_content = Adw.ButtonContent(icon_name="object-select-symbolic", label="Save and Apply")
        btn_save = Gtk.Button(child=save_content)
        btn_save.add_css_class("suggested-action")
        btn_save.set_tooltip_text("Save permanently to ~/.config/caelestia/hypr-vars.lua (Ctrl+S)")
        btn_save.connect("clicked", self.on_save_clicked)
        header.pack_end(btn_save)

        toolbar_view.add_top_bar(header)

        # Navigation Split View (Left categories, Right content)
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_min_sidebar_width(230)
        self.split_view.set_max_sidebar_width(290)

        self.stack = Adw.ViewStack()

        # Build Pages
        self.build_windows_page()
        self.build_blur_page()
        self.build_shadows_page()
        self.build_colors_page()
        self.build_fonts_page()
        self.build_input_page()
        self.build_animations_page()
        self.build_apps_page()
        self.build_gpu_page()

        # Sidebar with ViewSwitcherSidebar
        sidebar = Adw.ViewSwitcherSidebar(stack=self.stack)
        
        sidebar_nav_page = Adw.NavigationPage(child=sidebar, title="Settings")
        content_nav_page = Adw.NavigationPage(child=self.stack, title="Preferences")

        self.split_view.set_sidebar(sidebar_nav_page)
        self.split_view.set_content(content_nav_page)

        toolbar_view.set_content(self.split_view)

        # Keyboard shortcuts
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_ctrl)

    def on_key_pressed(self, controller, keyval, keycode, state):
        if (state & Gdk.ModifierType.CONTROL_MASK):
            if keyval == Gdk.KEY_s or keyval == Gdk.KEY_S:
                self.on_save_clicked(None)
                return True
            elif keyval == Gdk.KEY_q or keyval == Gdk.KEY_Q:
                self.close()
                return True
        return False

    def schedule_live_apply(self):
        """Debounce live application to 40ms to make slider dragging butter-smooth"""
        if self.apply_timeout_id is not None:
            GLib.source_remove(self.apply_timeout_id)
        self.apply_timeout_id = GLib.timeout_add(40, self._do_live_apply)

    def _do_live_apply(self):
        self.apply_timeout_id = None
        s = self.state

        lua_cmd = f"""
hl.config({{
    general = {{
        gaps_in = {int(s.get('windowGapsIn', 0))},
        gaps_out = {int(s.get('windowGapsOut', 0))},
        gaps_workspaces = {int(s.get('workspaceGaps', 20))},
        border_size = {int(s.get('windowBorderSize', 1))},
        layout = "{s.get('layout', 'dwindle')}",
        col = {{
            active_border = "{s.get('activeWindowBorderColour', 'rgba(c6c6c650)')}",
            inactive_border = "{s.get('inactiveWindowBorderColour', 'rgba(ababab11)')}"
        }}
    }},
    decoration = {{
        rounding = {int(s.get('windowRounding', 15))},
        active_opacity = {float(s.get('windowOpacity', 0.95)):.2f},
        inactive_opacity = {float(s.get('inactiveOpacity', 0.90)):.2f},
        dim_inactive = {'true' if s.get('dimInactive', False) else 'false'},
        dim_strength = {float(s.get('dimStrength', 0.15)):.2f},
        blur = {{
            enabled = {'true' if s.get('blurEnabled', True) else 'false'},
            size = {int(s.get('blurSize', 8))},
            passes = {int(s.get('blurPasses', 2))},
            xray = {'true' if s.get('blurXray', False) else 'false'},
            popups = {'true' if s.get('blurPopups', True) else 'false'},
            special = {'true' if s.get('blurSpecialWs', False) else 'false'},
            input_methods = {'true' if s.get('blurInputMethods', True) else 'false'}
        }},
        shadow = {{
            enabled = {'true' if s.get('shadowEnabled', True) else 'false'},
            range = {int(s.get('shadowRange', 15))},
            render_power = {int(s.get('shadowRenderPower', 4))},
            color = "{s.get('shadowColour', 'rgba(5f5f5f10)')}"
        }}
    }},
    animations = {{
        enabled = {'true' if s.get('animationsEnabled', True) else 'false'}
    }},
    input = {{
        sensitivity = {float(s.get('mouseSensitivity', 0.0)):.2f},
        accel_profile = "{s.get('mouseAccelProfile', 'flat')}",
        repeat_delay = {int(s.get('repeatDelay', 500))},
        repeat_rate = {int(s.get('repeatRate', 35))},
        touchpad = {{
            natural_scroll = {'true' if s.get('touchpadNaturalScroll', True) else 'false'},
            disable_while_typing = {'true' if s.get('touchpadDisableTyping', True) else 'false'},
            scroll_factor = {float(s.get('touchpadScrollFactor', 0.3)):.2f}
        }}
    }}
}})
hl.window_rule({{ match = {{ fullscreen = false }}, opacity = "{float(s.get('windowOpacity', 0.95)):.2f} override" }})
hl.window_rule({{ match = {{ class = "org.caelestia.hyprland.tweaker" }}, float = true, size = "920 650", center = true }})
hl.window_rule({{ match = {{ title = "Caelestia Hyprland Tweaker" }}, float = true, size = "920 650", center = true }})
local ok_vars, hvars = pcall(require, "variables")
if ok_vars and type(hvars) == "table" then
    hvars.volumeStep = {int(s.get('volumeStep', 5))}
    hvars.volumeMax = {int(s.get('volumeMax', 100))}
    hvars.brightnessStep = {int(s.get('brightnessStep', 5))}
end
"""
        try:
            # Run hyprctl eval asynchronously
            subprocess.Popen(["hyprctl", "eval", lua_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        return False

    def update_state_key(self, key, value):
        self.state[key] = value
        self.schedule_live_apply()

    def on_enable_border_toggled(self, active):
        if self._syncing_border:
            return
        self._syncing_border = True
        try:
            if not active:
                curr = int(self.state.get("windowBorderSize", 1))
                if curr > 0:
                    self.last_nonzero_border_size = curr
                target = 0
            else:
                target = getattr(self, "last_nonzero_border_size", 1)
                if target <= 0:
                    target = 1

            self.update_state_key("windowBorderSize", target)
            if hasattr(self, "row_bs"):
                self.row_bs.set_val(target)
            if hasattr(self, "row_enable_border"):
                self.row_enable_border.set_active(target > 0)
            if hasattr(self, "row_enable_border_colors"):
                self.row_enable_border_colors.set_active(target > 0)
        finally:
            self._syncing_border = False

    def on_border_size_changed(self, val):
        if self._syncing_border:
            return
        self._syncing_border = True
        try:
            val = int(val)
            if val > 0:
                self.last_nonzero_border_size = val
            is_active = val > 0
            if hasattr(self, "row_enable_border"):
                self.row_enable_border.set_active(is_active)
            if hasattr(self, "row_enable_border_colors"):
                self.row_enable_border_colors.set_active(is_active)
            self.update_state_key("windowBorderSize", val)
        finally:
            self._syncing_border = False

    def on_volume_step_changed(self, val):
        val = int(val)
        self.update_state_key("volumeStep", val)
        update_shell_step_live("audio", val)

    def on_brightness_step_changed(self, val):
        val = int(val)
        self.update_state_key("brightnessStep", val)
        update_shell_step_live("brightness", val)

    # --- TAB 1: WINDOWS and GAPS ---
    def build_windows_page(self):
        page = Adw.PreferencesPage(title="Windows and Gaps", icon_name="view-grid-symbolic")

        # Gaps Group
        grp_gaps = Adw.PreferencesGroup(title="Window Spacing and Gaps", description="Spacing between tiles and screen boundaries")
        
        row_gi = SliderRow("Inner Window Gaps", "Distance between adjacent tiled windows", 0, 50, 1, self.state["windowGapsIn"], unit="px", on_change=lambda v: self.update_state_key("windowGapsIn", v))
        self.slider_rows["windowGapsIn"] = row_gi
        grp_gaps.add(row_gi)

        row_go = SliderRow("Outer Window Gaps", "Distance between windows and monitor edges", 0, 50, 1, self.state["windowGapsOut"], unit="px", on_change=lambda v: self.update_state_key("windowGapsOut", v))
        self.slider_rows["windowGapsOut"] = row_go
        grp_gaps.add(row_go)

        row_wg = SliderRow("Workspace Gaps", "Margin between virtual workspaces", 0, 60, 1, self.state["workspaceGaps"], unit="px", on_change=lambda v: self.update_state_key("workspaceGaps", v))
        self.slider_rows["workspaceGaps"] = row_wg
        grp_gaps.add(row_wg)

        row_sw = SliderRow("Single Window Gap", "Outer margin when only one window is open", 0, 50, 1, self.state["singleWindowGapsOut"], unit="px", on_change=lambda v: self.update_state_key("singleWindowGapsOut", v))
        self.slider_rows["singleWindowGapsOut"] = row_sw
        grp_gaps.add(row_sw)

        page.add(grp_gaps)

        # Borders & Corners Group
        grp_border = Adw.PreferencesGroup(title="Borders and Corners", description="Corner curvature and border thickness")
        
        row_rnd = SliderRow("Corner Rounding", "Radius of curved window corners", 0, 40, 1, self.state["windowRounding"], unit="px", on_change=lambda v: self.update_state_key("windowRounding", v))
        self.slider_rows["windowRounding"] = row_rnd
        grp_border.add(row_rnd)

        self.row_enable_border = make_switch_row(
            "Enable Window Borders",
            "Show or completely remove border outlines around windows",
            int(self.state.get("windowBorderSize", 1)) > 0,
            on_change=self.on_enable_border_toggled
        )
        grp_border.add(self.row_enable_border)

        self.row_bs = SliderRow(
            "Border Thickness",
            "Window outline stroke width (0px = borderless)",
            0, 10, 1,
            self.state["windowBorderSize"],
            unit="px",
            on_change=self.on_border_size_changed
        )
        self.slider_rows["windowBorderSize"] = self.row_bs
        grp_border.add(self.row_bs)

        page.add(grp_border)

        # Opacity Group
        grp_opacity = Adw.PreferencesGroup(title="Window Translucency and Opacity", description="Transparency for focused and unfocused windows")
        
        row_ao = SliderRow("Active Window Opacity", "Transparency of currently focused window", 0.20, 1.00, 0.01, self.state["windowOpacity"], digits=2, on_change=lambda v: self.update_state_key("windowOpacity", v))
        self.slider_rows["windowOpacity"] = row_ao
        grp_opacity.add(row_ao)

        row_io = SliderRow("Inactive Window Opacity", "Transparency of background windows", 0.20, 1.00, 0.01, self.state["inactiveOpacity"], digits=2, on_change=lambda v: self.update_state_key("inactiveOpacity", v))
        self.slider_rows["inactiveOpacity"] = row_io
        grp_opacity.add(row_io)

        self.row_dim_inactive = make_switch_row(
            "Dim Inactive Windows",
            "Darken background windows to emphasize focus",
            self.state["dimInactive"],
            on_change=lambda v: self.update_state_key("dimInactive", v)
        )
        grp_opacity.add(self.row_dim_inactive)
        
        row_ds = SliderRow("Dimming Strength", "Intensity of background window darkening", 0.00, 0.80, 0.05, self.state["dimStrength"], digits=2, on_change=lambda v: self.update_state_key("dimStrength", v))
        self.slider_rows["dimStrength"] = row_ds
        grp_opacity.add(row_ds)

        page.add(grp_opacity)

        self.stack.add_titled_with_icon(page, "windows", "Windows and Gaps", "view-grid-symbolic")

    # --- TAB 2: BLUR and TRANSLUCENCY ---
    def build_blur_page(self):
        page = Adw.PreferencesPage(title="Blur and Translucency", icon_name="weather-fog-symbolic")

        grp_blur = Adw.PreferencesGroup(title="Blur Engine", description="Real-time GPU backdrop blur configuration")
        grp_blur.add(make_switch_row("Enable Background Blur", "Apply blur effects behind translucent surfaces", self.state["blurEnabled"], on_change=lambda v: self.update_state_key("blurEnabled", v)))
        
        row_bsz = SliderRow("Blur Size / Radius", "Radius of the blur kernel", 1, 25, 1, self.state["blurSize"], on_change=lambda v: self.update_state_key("blurSize", v))
        self.slider_rows["blurSize"] = row_bsz
        grp_blur.add(row_bsz)

        row_bps = SliderRow("Blur Passes", "Sampling iterations (higher = smoother, requires more GPU)", 1, 6, 1, self.state["blurPasses"], on_change=lambda v: self.update_state_key("blurPasses", v))
        self.slider_rows["blurPasses"] = row_bps
        grp_blur.add(row_bps)

        page.add(grp_blur)

        grp_surfaces = Adw.PreferencesGroup(title="Surfaces and Overlays", description="Choose which UI elements receive blur")
        grp_surfaces.add(make_switch_row("Blur Context Menus and Popups", "Apply blur behind context menus and dropdowns", self.state["blurPopups"], on_change=lambda v: self.update_state_key("blurPopups", v)))
        grp_surfaces.add(make_switch_row("Blur Special Workspaces", "Apply blur when scratchpad/special workspace is active", self.state["blurSpecialWs"], on_change=lambda v: self.update_state_key("blurSpecialWs", v)))
        grp_surfaces.add(make_switch_row("Blur Input Methods", "Apply blur behind on-screen keyboard and IME dialogs", self.state["blurInputMethods"], on_change=lambda v: self.update_state_key("blurInputMethods", v)))
        grp_surfaces.add(make_switch_row("X-Ray Mode", "Floating windows ignore other floating windows behind them", self.state["blurXray"], on_change=lambda v: self.update_state_key("blurXray", v)))
        page.add(grp_surfaces)

        self.stack.add_titled_with_icon(page, "blur", "Blur Effects", "weather-fog-symbolic")

    # --- TAB 3: SHADOWS ---
    def build_shadows_page(self):
        page = Adw.PreferencesPage(title="Drop Shadows", icon_name="weather-clear-night-symbolic")

        grp_shadow = Adw.PreferencesGroup(title="Window Drop Shadows", description="Ambient depth and window elevation")
        grp_shadow.add(make_switch_row("Enable Shadows", "Render drop shadows behind windows", self.state["shadowEnabled"], on_change=lambda v: self.update_state_key("shadowEnabled", v)))
        
        row_sr = SliderRow("Shadow Range", "Size and spread distance of shadows", 0, 60, 1, self.state["shadowRange"], unit="px", on_change=lambda v: self.update_state_key("shadowRange", v))
        self.slider_rows["shadowRange"] = row_sr
        grp_shadow.add(row_sr)

        row_sp = SliderRow("Shadow Render Power", "Hardness falloff curve (1=soft ambient, 4=sharp shadow)", 1, 4, 1, self.state["shadowRenderPower"], on_change=lambda v: self.update_state_key("shadowRenderPower", v))
        self.slider_rows["shadowRenderPower"] = row_sp
        grp_shadow.add(row_sp)

        grp_shadow.add(ColorPickerRow("Shadow Color and Opacity", "Ambient shadow hue", self.state["shadowColour"], on_change=lambda v: self.update_state_key("shadowColour", v)))
        page.add(grp_shadow)

        self.stack.add_titled_with_icon(page, "shadows", "Drop Shadows", "weather-clear-night-symbolic")

    # --- TAB 4: BORDERS and COLORS ---
    def build_colors_page(self):
        page = Adw.PreferencesPage(title="Borders and Colors", icon_name="color-select-symbolic")

        # Group 1: Window Border Colors
        grp_borders = Adw.PreferencesGroup(
            title="Window Border Colors",
            description="Customize outline colors and transparency for active and inactive windows"
        )
        self.row_enable_border_colors = make_switch_row(
            "Enable Window Borders",
            "Show or completely remove border outlines around windows",
            int(self.state.get("windowBorderSize", 1)) > 0,
            on_change=self.on_enable_border_toggled
        )
        grp_borders.add(self.row_enable_border_colors)

        self.row_active_color = ColorPickerRow(
            "Active Window Border",
            "Color and glow of the currently focused window",
            self.state["activeWindowBorderColour"],
            on_change=lambda v: self.update_state_key("activeWindowBorderColour", v)
        )
        self.row_inactive_color = ColorPickerRow(
            "Inactive Window Border",
            "Color of unfocused background windows",
            self.state["inactiveWindowBorderColour"],
            on_change=lambda v: self.update_state_key("inactiveWindowBorderColour", v)
        )
        grp_borders.add(self.row_active_color)
        grp_borders.add(self.row_inactive_color)
        page.add(grp_borders)

        # Group 2: Curated Palette Presets
        grp_presets = Adw.PreferencesGroup(
            title="Curated Color Palettes",
            description="Select or apply popular themes to instantly style your window borders"
        )

        presets = [
            {
                "name": "Caelestia Dynamic",
                "desc": "Harmonized with your wallpaper and Material You scheme",
                "active": f"rgba({self.scheme_colors['primary']}50)",
                "inactive": f"rgba({self.scheme_colors['onSurfaceVariant']}11)",
                "act_class": "swatch-caelestia-act",
                "inact_class": "swatch-caelestia-inact",
            },
            {
                "name": "Neon Cyan (Cyberpunk)",
                "desc": "Luminescent turquoise (#80f0e7) on dark slate (#102025)",
                "active": "rgba(80f0e7ee)",
                "inactive": "rgba(10202533)",
                "act_class": "swatch-cyan-act",
                "inact_class": "swatch-cyan-inact",
            },
            {
                "name": "Catppuccin Mauve",
                "desc": "Soft pastel purple (#cba6f7) on mocha slate (#313244)",
                "active": "rgba(cba6f7ee)",
                "inactive": "rgba(31324466)",
                "act_class": "swatch-catppuccin-act",
                "inact_class": "swatch-catppuccin-inact",
            },
            {
                "name": "Nord Frost",
                "desc": "Arctic cool ice blue (#88c0d0) on deep polar night (#2e3440)",
                "active": "rgba(88c0d0ee)",
                "inactive": "rgba(2e344066)",
                "act_class": "swatch-nord-act",
                "inact_class": "swatch-nord-inact",
            },
            {
                "name": "Tokyo Night",
                "desc": "Vivid midnight blue (#7aa2f7) on storm night (#1a1b26)",
                "active": "rgba(7aa2f7ee)",
                "inactive": "rgba(1a1b2666)",
                "act_class": "swatch-tokyo-act",
                "inact_class": "swatch-tokyo-inact",
            },
            {
                "name": "Gruvbox Warm",
                "desc": "Retro warm amber (#fabd2f) on dark espresso (#3c3836)",
                "active": "rgba(fabd2fee)",
                "inactive": "rgba(3c383666)",
                "act_class": "swatch-gruvbox-act",
                "inact_class": "swatch-gruvbox-inact",
            },
        ]

        for p in presets:
            row = Adw.ActionRow(title=p["name"], subtitle=p["desc"])
            row.set_activatable(True)
            
            # Swatch pair preview
            swatches = make_swatch_pair(p["act_class"], p["inact_class"])
            row.add_prefix(swatches)

            # Apply button
            btn_apply = Gtk.Button(label="Apply")
            btn_apply.set_valign(Gtk.Align.CENTER)
            btn_apply.add_css_class("flat")
            btn_apply.connect("clicked", lambda b, pr=p: self.apply_preset(pr["name"], pr["active"], pr["inactive"]))
            row.add_suffix(btn_apply)

            # Clicking row also applies
            row.connect("activated", lambda r, pr=p: self.apply_preset(pr["name"], pr["active"], pr["inactive"]))
            grp_presets.add(row)

        page.add(grp_presets)
        self.stack.add_titled_with_icon(page, "colors", "Borders and Colors", "color-select-symbolic")

    def apply_preset(self, name, active, inactive):
        self.state["activeWindowBorderColour"] = active
        self.state["inactiveWindowBorderColour"] = inactive
        self.row_active_color.set_color(active)
        self.row_inactive_color.set_color(inactive)
        self.schedule_live_apply()
        self.toast_overlay.add_toast(Adw.Toast.new(f"Applied '{name}' palette"))

    # --- TAB 5: FONTS and CURSORS ---
    def build_fonts_page(self):
        page = Adw.PreferencesPage(title="Fonts and Cursors", icon_name="font-x-generic-symbolic")

        grp_fonts = Adw.PreferencesGroup(title="System and Interface Fonts", description="Live typography applied to GTK applications and shell elements")
        grp_fonts.add(FontRow("Interface Font", "System UI, menus, and window labels", self.state["interfaceFont"], on_change=self.on_interface_font_changed))
        grp_fonts.add(FontRow("Monospace Font", "Default code editor, terminal, and monospace font", self.state["monospaceFont"], on_change=self.on_mono_font_changed))
        page.add(grp_fonts)

        grp_cursor = Adw.PreferencesGroup(title="Mouse Cursor Theme", description="Pointer style and scale")
        cursor_themes = get_installed_cursor_themes()
        grp_cursor.add(ComboRow("Cursor Theme", "Installed cursor icon pack", cursor_themes, self.state["cursorTheme"], on_change=self.on_cursor_theme_changed))
        
        row_csz = SliderRow("Cursor Size", "Pointer size in pixels", 16, 64, 2, self.state["cursorSize"], unit="px", on_change=self.on_cursor_size_changed)
        self.slider_rows["cursorSize"] = row_csz
        grp_cursor.add(row_csz)
        
        page.add(grp_cursor)

        self.stack.add_titled_with_icon(page, "fonts", "Fonts and Cursors", "font-x-generic-symbolic")

    def on_interface_font_changed(self, font_name):
        self.state["interfaceFont"] = font_name
        set_gsettings("font-name", font_name)

    def on_mono_font_changed(self, font_name):
        self.state["monospaceFont"] = font_name
        set_gsettings("monospace-font-name", font_name)
        update_foot_font(font_name)

    def update_cursor_live(self, theme, size):
        theme_str = str(theme)
        size_int = int(size)

        # 1. Update running app GtkSettings immediately so the cursor changes right under the user's hand!
        try:
            gtk_settings = Gtk.Settings.get_default()
            if gtk_settings:
                gtk_settings.set_property("gtk-cursor-theme-name", theme_str)
                gtk_settings.set_property("gtk-cursor-theme-size", size_int)
        except Exception:
            pass

        # 2. Update gsettings (Wayland / GNOME desktop interface)
        set_gsettings("cursor-theme", theme_str)
        set_gsettings("cursor-size", size_int, is_string=False)

        # 3. Update gtk-3.0 and gtk-4.0 settings.ini
        update_gtk_settings_ini("gtk-cursor-theme-name", theme_str)
        update_gtk_settings_ini("gtk-cursor-theme-size", size_int)
        update_default_cursor_theme(theme_str)

        # 4. Tell Hyprland to update cursor for compositor and root surfaces
        try:
            subprocess.run(["hyprctl", "setcursor", theme_str, str(size_int)], check=False)
        except Exception:
            pass

        # 5. Tell Hyprland to update environment variables
        try:
            lua_cmd = f"hl.env('XCURSOR_SIZE', '{size_int}'); hl.env('HYPRCURSOR_SIZE', '{size_int}'); hl.env('XCURSOR_THEME', '{theme_str}'); hl.env('HYPRCURSOR_THEME', '{theme_str}')"
            subprocess.Popen(["hyprctl", "eval", lua_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def on_cursor_theme_changed(self, theme_name):
        self.state["cursorTheme"] = theme_name
        self.update_cursor_live(theme_name, self.state.get("cursorSize", 24))

    def on_cursor_size_changed(self, size):
        self.state["cursorSize"] = int(size)
        self.update_cursor_live(self.state.get("cursorTheme", "Qogir-white-cursors"), int(size))

    # --- TAB 6: INPUT and TOUCHPAD ---
    def build_input_page(self):
        page = Adw.PreferencesPage(title="Input and Touchpad", icon_name="input-mouse-symbolic")

        grp_touchpad = Adw.PreferencesGroup(title="Touchpad Configuration", description="Palm rejection and scroll behavior")
        grp_touchpad.add(make_switch_row("Disable While Typing", "Prevent accidental palm jumps while typing on keyboard", self.state["touchpadDisableTyping"], on_change=lambda v: self.update_state_key("touchpadDisableTyping", v)))
        grp_touchpad.add(make_switch_row("Natural Scrolling", "Content tracks fingertip movement direction", self.state["touchpadNaturalScroll"], on_change=lambda v: self.update_state_key("touchpadNaturalScroll", v)))
        
        row_sf = SliderRow("Scroll Speed Factor", "Touchpad scroll velocity multiplier", 0.1, 1.5, 0.05, self.state["touchpadScrollFactor"], digits=2, on_change=lambda v: self.update_state_key("touchpadScrollFactor", v))
        self.slider_rows["touchpadScrollFactor"] = row_sf
        grp_touchpad.add(row_sf)
        page.add(grp_touchpad)

        grp_pointer = Adw.PreferencesGroup(title="Mouse and Pointer Acceleration", description="Tracking sensitivity and cursor speed")
        row_ms = SliderRow("Mouse Sensitivity", "Raw pointer speed multiplier (-1.0 to 1.0)", -1.0, 1.0, 0.05, self.state["mouseSensitivity"], digits=2, on_change=lambda v: self.update_state_key("mouseSensitivity", v))
        self.slider_rows["mouseSensitivity"] = row_ms
        grp_pointer.add(row_ms)

        grp_pointer.add(ComboRow("Acceleration Profile", "Mouse acceleration curve algorithm", ["flat", "adaptive"], self.state["mouseAccelProfile"], on_change=lambda v: self.update_state_key("mouseAccelProfile", v)))
        page.add(grp_pointer)

        # Multi-touch Gestures (Clean Dropdown Menus instead of Sliders)
        grp_gestures = Adw.PreferencesGroup(title="Multi-touch Gestures", description="Touchpad gesture finger count for workspace transitions")

        spec_val = int(self.state.get("gestureFingers", 3))
        spec_str = f"{spec_val} Fingers" if spec_val in [3, 4] else "3 Fingers"
        combo_spec = ComboRow(
            "Special Workspace Swipe",
            "Fingers required to swipe vertically into the scratchpad",
            ["3 Fingers", "4 Fingers"],
            spec_str,
            on_change=lambda item: self.update_state_key("gestureFingers", int(item.split()[0]))
        )
        grp_gestures.add(combo_spec)

        ws_val = int(self.state.get("workspaceSwipeFingers", 4))
        ws_str = f"{ws_val} Fingers" if ws_val in [3, 4] else "4 Fingers"
        combo_ws = ComboRow(
            "Desktop Workspace Swipe",
            "Fingers required to swipe horizontally between desktop workspaces",
            ["3 Fingers", "4 Fingers"],
            ws_str,
            on_change=lambda item: self.update_state_key("workspaceSwipeFingers", int(item.split()[0]))
        )
        grp_gestures.add(combo_ws)

        sleep_val = int(self.state.get("gestureFingersMore", 4))
        sleep_str = "4 Fingers Down" if sleep_val == 4 else "Disabled"
        combo_sleep = ComboRow(
            "System Sleep Gesture",
            "Fingers required to swipe down to suspend the system",
            ["4 Fingers Down", "Disabled"],
            sleep_str,
            on_change=lambda item: self.update_state_key("gestureFingersMore", 4 if "4" in item else 0)
        )
        grp_gestures.add(combo_sleep)

        page.add(grp_gestures)

        # Keyboard Repeat Configuration
        grp_kbd = Adw.PreferencesGroup(title="Keyboard Repeat", description="Key press delay and repeat speed")
        row_rd = SliderRow("Repeat Delay", "Delay before a held key starts repeating (500ms prevents wake-up multi-typing)", 200, 1000, 50, self.state.get("repeatDelay", 500), unit="ms", on_change=lambda v: self.update_state_key("repeatDelay", int(v)))
        self.slider_rows["repeatDelay"] = row_rd
        grp_kbd.add(row_rd)

        row_rr = SliderRow("Repeat Rate", "Characters generated per second while holding a key", 10, 60, 5, self.state.get("repeatRate", 35), unit="/s", on_change=lambda v: self.update_state_key("repeatRate", int(v)))
        self.slider_rows["repeatRate"] = row_rr
        grp_kbd.add(row_rr)
        page.add(grp_kbd)

        self.stack.add_titled_with_icon(page, "input", "Input and Touchpad", "input-mouse-symbolic")

    # --- TAB 7: ANIMATIONS and LAYOUT ---
    def build_animations_page(self):
        page = Adw.PreferencesPage(title="Animations and Layout", icon_name="media-playback-start-symbolic")

        grp_anim = Adw.PreferencesGroup(title="Compositor Animations and Layout", description="Tiling mode and motion fluidity")
        grp_anim.add(make_switch_row("Enable Animations", "Smooth window open/close, resize, and workspace transitions", self.state["animationsEnabled"], on_change=lambda v: self.update_state_key("animationsEnabled", v)))
        grp_anim.add(ComboRow("Tiling Layout", "Active Hyprland window tiling layout manager", ["dwindle", "master"], self.state["layout"], on_change=lambda v: self.update_state_key("layout", v)))
        page.add(grp_anim)

        grp_hardware = Adw.PreferencesGroup(
            title="Volume and Brightness Step Controls",
            description="Percentage adjustments per keyboard hotkey press and shell scroll"
        )
        row_vs = SliderRow(
            "Volume Step",
            "Percentage change per volume key press and shell scroll",
            1, 20, 1,
            self.state["volumeStep"],
            unit="%",
            on_change=self.on_volume_step_changed
        )
        self.slider_rows["volumeStep"] = row_vs
        grp_hardware.add(row_vs)

        row_bs = SliderRow(
            "Brightness Step",
            "Percentage change per brightness key press and shell scroll",
            1, 20, 1,
            self.state["brightnessStep"],
            unit="%",
            on_change=self.on_brightness_step_changed
        )
        self.slider_rows["brightnessStep"] = row_bs
        grp_hardware.add(row_bs)

        row_vm = SliderRow(
            "Max Volume Limit",
            "Upper volume ceiling (allow audio amplification)",
            100, 150, 5,
            self.state["volumeMax"],
            unit="%",
            on_change=lambda v: self.update_state_key("volumeMax", v)
        )
        self.slider_rows["volumeMax"] = row_vm
        grp_hardware.add(row_vm)

        page.add(grp_hardware)

        self.stack.add_titled_with_icon(page, "animations", "Animations and Layout", "media-playback-start-symbolic")

    # --- TAB 8: DEFAULT APPS ---
    def build_apps_page(self):
        page = Adw.PreferencesPage(title="Default Applications", icon_name="system-run-symbolic")

        grp_apps = Adw.PreferencesGroup(title="Caelestia Default Applications", description="Programs triggered by Caelestia hotkeys and app launchers")
        
        row_term = Adw.EntryRow(title="Terminal Emulator", text=str(self.state.get("terminal", "foot")))
        row_term.connect("notify::text", lambda r, p: self.state.update({"terminal": r.get_text()}))
        grp_apps.add(row_term)

        row_browser = Adw.EntryRow(title="Web Browser", text=str(self.state.get("browser", "zen-browser")))
        row_browser.connect("notify::text", lambda r, p: self.state.update({"browser": r.get_text()}))
        grp_apps.add(row_browser)

        row_editor = Adw.EntryRow(title="Code and Text Editor", text=str(self.state.get("editor", "codium")))
        row_editor.connect("notify::text", lambda r, p: self.state.update({"editor": r.get_text()}))
        grp_apps.add(row_editor)

        row_files = Adw.EntryRow(title="File Manager", text=str(self.state.get("fileExplorer", "nautilus")))
        row_files.connect("notify::text", lambda r, p: self.state.update({"fileExplorer": r.get_text()}))
        grp_apps.add(row_files)

        row_audio = Adw.EntryRow(title="Audio Settings GUI", text=str(self.state.get("audioSettings", "pavucontrol")))
        row_audio.connect("notify::text", lambda r, p: self.state.update({"audioSettings": r.get_text()}))
        grp_apps.add(row_audio)

        page.add(grp_apps)
        self.stack.add_titled_with_icon(page, "apps", "Default Apps", "system-run-symbolic")

    def build_gpu_page(self):
        page = Adw.PreferencesPage(title="Graphics and GPU", icon_name="video-display-symbolic")

        # Hardware Info Group
        grp_hw = Adw.PreferencesGroup(
            title="Detected Graphics Hardware",
            description="Graphics processors and active compositor renderer"
        )
        gpu_info = detect_gpus_info()
        active_renderer = get_current_hyprland_gpu()

        row_igpu = Adw.ActionRow(
            title="Integrated GPU (iGPU)",
            subtitle=gpu_info.get("igpu") or "Intel Raptor Lake UHD Graphics (/dev/dri/card1)"
        )
        grp_hw.add(row_igpu)

        row_dgpu = Adw.ActionRow(
            title="Dedicated GPU (dGPU)",
            subtitle=gpu_info.get("dgpu") or "NVIDIA GeForce RTX 4050 (/dev/dri/card2)"
        )
        grp_hw.add(row_dgpu)

        row_active = Adw.ActionRow(
            title="Active Hyprland Renderer",
            subtitle=active_renderer
        )
        grp_hw.add(row_active)
        page.add(grp_hw)

        # GPU Selection Group
        grp_mode = Adw.PreferencesGroup(
            title="Hyprland and Caelestia Shell Renderer",
            description="Choose which GPU renders the Hyprland compositor, Caelestia Shell, and desktop effects"
        )

        gpu_options = [
            "Integrated GPU (Intel UHD - Power Saving / Quiet)",
            "Dedicated GPU (NVIDIA RTX 4050 - High Performance)"
        ]
        current_mode = self.state.get("primaryGpu", "intel")
        current_label = gpu_options[1] if current_mode == "nvidia" else gpu_options[0]

        def on_gpu_changed(label):
            if "NVIDIA" in label:
                self.state["primaryGpu"] = "nvidia"
            else:
                self.state["primaryGpu"] = "intel"

        self.gpu_combo_row = ComboRow(
            title="Primary Rendering GPU",
            subtitle="Configures AQ_DRM_DEVICES device priority in Hyprland",
            items=gpu_options,
            current_item=current_label,
            on_change=on_gpu_changed
        )
        grp_mode.add(self.gpu_combo_row)

        row_restart = Adw.ActionRow(
            title="Session Restart Required",
            subtitle="Changes take effect on next Hyprland login. Click 'Save and Apply' first, then log out."
        )
        btn_logout = Gtk.Button(label="Log Out", icon_name="system-log-out-symbolic")
        btn_logout.add_css_class("destructive-action")
        btn_logout.set_valign(Gtk.Align.CENTER)
        btn_logout.connect("clicked", self.on_logout_clicked)
        row_restart.add_suffix(btn_logout)
        grp_mode.add(row_restart)

        page.add(grp_mode)

        # On-Demand Execution Group
        grp_prime = Adw.PreferencesGroup(
            title="On-Demand Application Offloading",
            description="Run heavy apps or games on NVIDIA dGPU without switching the desktop shell"
        )
        row_prime = Adw.ActionRow(
            title="Command Line Prefix",
            subtitle="Launch apps on NVIDIA dGPU via: prime-run &lt;app&gt;"
        )
        grp_prime.add(row_prime)

        row_steam = Adw.ActionRow(
            title="Steam Launch Option",
            subtitle="In Steam game properties, set Launch Options to: prime-run %command%"
        )
        grp_prime.add(row_steam)

        # Intel Display Power Saving (PSR) Group
        grp_psr = Adw.PreferencesGroup(
            title="Intel Display Power Saving (PSR)",
            description="Control Panel Self Refresh to eliminate idle mouse stutters and typing freezes"
        )

        psr_info = psr_helper.get_status()
        self.psr_enabled = not psr_info.get("configured_disabled", False)
        self._updating_psr = False

        self.row_psr = Adw.SwitchRow(
            title="Panel Self Refresh (PSR)",
            active=self.psr_enabled
        )

        self.row_psr_status = Adw.ActionRow(
            title="Current Hardware Status"
        )
        self.btn_psr_reboot = Gtk.Button(label="Reboot Now", icon_name="system-reboot-symbolic")
        self.btn_psr_reboot.add_css_class("destructive-action")
        self.btn_psr_reboot.set_valign(Gtk.Align.CENTER)
        self.btn_psr_reboot.connect("clicked", self.on_psr_reboot_clicked)
        self.row_psr_status.add_suffix(self.btn_psr_reboot)

        def update_psr_ui():
            status = psr_helper.get_status()
            has_intel = status.get("has_intel", False)
            if not has_intel:
                self.row_psr.set_sensitive(False)
                self.row_psr.set_subtitle("No Intel integrated graphics detected on this system")
                self.row_psr_status.set_subtitle("Not supported on this hardware")
                self.btn_psr_reboot.set_visible(False)
                return

            sk = status.get("state_key", "enabled")
            if sk == "disabled":
                self.row_psr.set_subtitle("Disabled — Wake-up stutters and typing lag eliminated")
                self.row_psr_status.set_subtitle("Disabled (Active in current boot session)")
                self.btn_psr_reboot.set_visible(False)
            elif sk == "disabled_pending_reboot":
                self.row_psr.set_subtitle("Disabled in GRUB — System reboot required to take effect")
                self.row_psr_status.set_subtitle("Disabled in boot config (Reboot required)")
                self.btn_psr_reboot.set_visible(True)
            elif sk == "enabled_pending_reboot":
                self.row_psr.set_subtitle("Enabled in GRUB — System reboot required to take effect")
                self.row_psr_status.set_subtitle("Enabled in boot config (Reboot required)")
                self.btn_psr_reboot.set_visible(True)
            else:
                self.row_psr.set_subtitle("Enabled — Screen power saving active (may cause wake stutter)")
                self.row_psr_status.set_subtitle("Enabled (Active in current boot session)")
                self.btn_psr_reboot.set_visible(False)

        def on_psr_toggled(switch_row, param):
            if getattr(self, "_updating_psr", False):
                return

            new_target = self.row_psr.get_active()
            action_name = "Enable" if new_target else "Disable"

            if not new_target:
                heading = "Disable Panel Self Refresh (PSR)?"
                body = (
                    "Disabling PSR prevents the Intel display engine from going to sleep while idle, "
                    "which permanently eliminates mouse stutters and repeated character typing bugs.\n\n"
                    "• Cost: ~0.5W–1.0W slightly higher idle battery draw\n"
                    "• Changes: Updates /etc/default/grub & /etc/modprobe.d/i915-psr.conf\n"
                    "• Administrator password (Polkit) will be requested\n"
                    "• A system reboot is required for hardware changes to apply"
                )
            else:
                heading = "Enable Panel Self Refresh (PSR)?"
                body = (
                    "Enabling PSR allows your laptop display to power down the display engine when idle "
                    "to slightly reduce battery consumption.\n\n"
                    "• Note: May re-introduce mouse stutter and typing lag when waking from idle\n"
                    "• Administrator password (Polkit) will be requested\n"
                    "• A system reboot is required for hardware changes to apply"
                )

            dialog = Adw.MessageDialog(
                transient_for=self,
                heading=heading,
                body=body
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("confirm", f"{action_name} PSR")
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.SUGGESTED)

            def on_dialog_response(d, resp):
                if resp != "confirm":
                    self._updating_psr = True
                    self.row_psr.set_active(not new_target)
                    self._updating_psr = False
                    return

                self.row_psr.set_sensitive(False)
                self.toast_overlay.add_toast(Adw.Toast.new(f"Applying PSR {action_name.lower()} configuration..."))

                def worker():
                    action_arg = "enable" if new_target else "disable"
                    real_dir = os.path.dirname(os.path.realpath(__file__))
                    helper_py = os.path.join(real_dir, "psr_helper.py")
                    if not os.path.isfile(helper_py):
                        for cand in [
                            os.path.join(real_dir, "caelestia_psr_helper.py"),
                            os.path.expanduser("~/.local/share/hypr-tweaker/src/psr_helper.py"),
                            "/usr/share/hypr-tweaker/src/psr_helper.py",
                            "/usr/local/share/hypr-tweaker/src/psr_helper.py",
                            os.path.expanduser("~/.local/share/caelestia-hypr-tweaker/caelestia_psr_helper.py")
                        ]:
                            if os.path.isfile(cand):
                                helper_py = cand
                                break
                    cmd = ["pkexec", sys.executable, helper_py, action_arg]
                    proc = subprocess.run(cmd, capture_output=True, text=True)
                    GLib.idle_add(on_apply_complete, proc.returncode, proc.stdout, proc.stderr, new_target, action_name)

                threading.Thread(target=worker, daemon=True).start()

            def on_apply_complete(returncode, stdout_output, stderr_output, target_val, act_name):
                self.row_psr.set_sensitive(True)
                if returncode == 0:
                    update_psr_ui()
                    reboot_dialog = Adw.MessageDialog(
                        transient_for=self,
                        heading=f"PSR Successfully {act_name}d",
                        body=(
                            f"Panel Self Refresh has been {act_name.lower()}d in the bootloader configuration.\n\n"
                            "Please restart your laptop for the hardware change to take effect."
                        )
                    )
                    reboot_dialog.add_response("later", "Reboot Later")
                    reboot_dialog.add_response("reboot", "Reboot Now")
                    reboot_dialog.set_response_appearance("reboot", Adw.ResponseAppearance.DESTRUCTIVE)

                    def on_reboot_resp(d, r_id):
                        if r_id == "reboot":
                            subprocess.run(["systemctl", "reboot"], check=False)

                    reboot_dialog.connect("response", on_reboot_resp)
                    reboot_dialog.present()
                else:
                    self._updating_psr = True
                    self.row_psr.set_active(not target_val)
                    self._updating_psr = False
                    update_psr_ui()
                    err_detail = (stderr_output or stdout_output or "").strip()
                    print(f"PSR apply error ({returncode}): {err_detail}", file=sys.stderr)
                    if "dismissed" in err_detail.lower() or returncode in (126, 127):
                        err_msg = "Authentication cancelled."
                    elif err_detail:
                        err_msg = f"Failed: {err_detail.splitlines()[-1][:80]}"
                    else:
                        err_msg = "Authentication failed or error occurred."
                    self.toast_overlay.add_toast(Adw.Toast.new(err_msg))

            dialog.connect("response", on_dialog_response)
            dialog.present()

        self.row_psr.connect("notify::active", on_psr_toggled)
        update_psr_ui()

        grp_psr.add(self.row_psr)
        grp_psr.add(self.row_psr_status)
        page.add(grp_psr)

        page.add(grp_prime)

        self.stack.add_titled_with_icon(page, "gpu", "Graphics and GPU", "video-display-symbolic")

    def on_logout_clicked(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Log Out of Hyprland?",
            body="Make sure you have clicked 'Save and Apply' to save your GPU settings before logging out."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("logout", "Log Out Now")
        dialog.set_response_appearance("logout", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(d, response_id):
            if response_id == "logout":
                subprocess.run(["hyprctl", "dispatch", "exit"], check=False)

        dialog.connect("response", on_response)
        dialog.present()

    def on_psr_reboot_clicked(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Reboot System?",
            body="A system reboot is required to apply the updated kernel display power settings."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reboot", "Reboot Now")
        dialog.set_response_appearance("reboot", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(d, response_id):
            if response_id == "reboot":
                subprocess.run(["systemctl", "reboot"], check=False)

        dialog.connect("response", on_response)
        dialog.present()

    # --- ACTIONS: RESET and SAVE ---
    def on_reset_clicked(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Reset to Caelestia Defaults?",
            body="This will reset all window spacing, blur, and styling options back to standard Caelestia defaults."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reset", "Reset Settings")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def on_response(d, response_id):
            if response_id == "reset":
                defaults_to_apply = {
                    "windowGapsIn": 5,
                    "windowGapsOut": 10,
                    "workspaceGaps": 20,
                    "singleWindowGapsOut": 5,
                    "windowRounding": 15,
                    "windowBorderSize": 1,
                    "windowOpacity": 0.95,
                    "inactiveOpacity": 0.90,
                    "dimInactive": False,
                    "dimStrength": 0.15,
                    "volumeStep": 5,
                    "volumeMax": 100,
                    "brightnessStep": 5,
                    "blurEnabled": True,
                    "blurSize": 8,
                    "blurPasses": 2,
                    "shadowEnabled": True,
                    "shadowRange": 15,
                    "shadowRenderPower": 4,
                    "repeatDelay": 500,
                    "repeatRate": 35,
                }
                for k, v in defaults_to_apply.items():
                    self.state[k] = v
                    if k in self.slider_rows:
                        self.slider_rows[k].set_val(v)

                self.last_nonzero_border_size = 1
                if hasattr(self, "row_enable_border"):
                    self.row_enable_border.set_active(True)
                if hasattr(self, "row_enable_border_colors"):
                    self.row_enable_border_colors.set_active(True)
                if hasattr(self, "row_dim_inactive"):
                    self.row_dim_inactive.set_active(False)

                update_shell_step_live("brightness", 5)
                update_shell_step_live("audio", 5)

                self.state["primaryGpu"] = "intel"
                if hasattr(self, "gpu_combo_row"):
                    self.gpu_combo_row.set_selected(0)

                self.apply_preset(
                    "Caelestia Dynamic",
                    f"rgba({self.scheme_colors['primary']}50)",
                    f"rgba({self.scheme_colors['onSurfaceVariant']}11)"
                )
                self.schedule_live_apply()
                self.toast_overlay.add_toast(Adw.Toast.new("Reset to factory defaults. Click 'Save and Apply' to keep."))

        dialog.connect("response", on_response)
        dialog.present()

    def on_save_clicked(self, btn):
        s = self.state
        os.makedirs(CAELESTIA_CONF_DIR, exist_ok=True)

        # Format border colors (preserving scheme if unchanged or raw string)
        act_col = str(s.get("activeWindowBorderColour", ""))
        inact_col = str(s.get("inactiveWindowBorderColour", ""))
        shadow_col = str(s.get("shadowColour", ""))

        lua_output = f"""-- Caelestia Hyprland User Variables Configuration
-- Managed visually by Caelestia Hyprland Tweaker
local scheme = require("scheme.current")

return {{
    -- Applications
    browser                    = "{s.get('browser', 'zen-browser')}",
    fileExplorer               = "{s.get('fileExplorer', 'nautilus')}",
    editor                     = "{s.get('editor', 'codium')}",
    terminal                   = "{s.get('terminal', 'foot')}",
    audioSettings              = "{s.get('audioSettings', 'pavucontrol')}",

    -- Cursor and Fonts
    cursorTheme                = "{s.get('cursorTheme', 'capitaine-cursors-light')}",
    cursorSize                 = {int(s.get('cursorSize', 24))},

    -- Window Gaps and Geometry
    windowGapsIn               = {int(s.get('windowGapsIn', 0))},
    windowGapsOut              = {int(s.get('windowGapsOut', 0))},
    workspaceGaps              = {int(s.get('workspaceGaps', 20))},
    singleWindowGapsOut        = {int(s.get('singleWindowGapsOut', 5))},

    -- Styling and Borders
    windowRounding             = {int(s.get('windowRounding', 15))},
    windowBorderSize           = {int(s.get('windowBorderSize', 1))},
    windowOpacity              = {float(s.get('windowOpacity', 0.95)):.2f},
    inactiveOpacity            = {float(s.get('inactiveOpacity', 0.90)):.2f},
    dimInactive                = {'true' if s.get('dimInactive', False) else 'false'},
    dimStrength                = {float(s.get('dimStrength', 0.15)):.2f},
    activeWindowBorderColour   = "{act_col}",
    inactiveWindowBorderColour = "{inact_col}",

    -- Blur
    blurEnabled                = {'true' if s.get('blurEnabled', True) else 'false'},
    blurSize                   = {int(s.get('blurSize', 8))},
    blurPasses                 = {int(s.get('blurPasses', 2))},
    blurXray                   = {'true' if s.get('blurXray', False) else 'false'},
    blurPopups                 = {'true' if s.get('blurPopups', True) else 'false'},
    blurInputMethods           = {'true' if s.get('blurInputMethods', True) else 'false'},
    blurSpecialWs              = {'true' if s.get('blurSpecialWs', False) else 'false'},

    -- Drop Shadows
    shadowEnabled              = {'true' if s.get('shadowEnabled', True) else 'false'},
    shadowRange                = {int(s.get('shadowRange', 15))},
    shadowRenderPower          = {int(s.get('shadowRenderPower', 4))},
    shadowColour               = "{shadow_col}",

    -- Touchpad and Gestures
    touchpadDisableTyping      = {'true' if s.get('touchpadDisableTyping', True) else 'false'},
    touchpadScrollFactor       = {float(s.get('touchpadScrollFactor', 0.3)):.2f},
    touchpadNaturalScroll      = {'true' if s.get('touchpadNaturalScroll', True) else 'false'},
    gestureFingers             = {int(s.get('gestureFingers', 3))},
    workspaceSwipeFingers      = {int(s.get('workspaceSwipeFingers', 4))},
    gestureFingersMore         = {int(s.get('gestureFingersMore', 4))},

    -- Animations
    animationsEnabled          = {'true' if s.get('animationsEnabled', True) else 'false'},

    -- Input
    mouseSensitivity           = {float(s.get('mouseSensitivity', 0.0)):.2f},
    mouseAccelProfile          = "{s.get('mouseAccelProfile', 'flat')}",
    repeatDelay                = {int(s.get('repeatDelay', 500))},
    repeatRate                 = {int(s.get('repeatRate', 35))},

    -- System, Volume and Hardware Steps
    volumeStep                 = {int(s.get('volumeStep', 5))},
    volumeMax                  = {int(s.get('volumeMax', 100))},
    brightnessStep             = {int(s.get('brightnessStep', 5))},

    -- Graphics and GPU (Hyprland & Shell Renderer)
    primaryGpu                 = "{s.get('primaryGpu', 'intel')}",
}}
"""
        try:
            # 1. Save standard Hyprland config (universally compatible with all Hyprland setups)
            try:
                os.makedirs(HYPR_CONF_DIR, exist_ok=True)
                act_hypr = format_hypr_color(act_col, "rgba(c6c6c688)")
                inact_hypr = format_hypr_color(inact_col, "rgba(26262688)")
                shadow_hypr = format_hypr_color(shadow_col, "rgba(00000044)")
                
                hypr_conf_content = f"""# =============================================================================
# Hypr Tweaker Configuration
# Automatically generated by Hypr Tweaker (https://github.com/iballz/hypr-tweaker)
# To source in hyprland.conf: source = ~/.config/hypr/hypr-tweaker.conf
# =============================================================================

general {{
    gaps_in = {int(s.get('windowGapsIn', 0))}
    gaps_out = {int(s.get('windowGapsOut', 0))}
    border_size = {int(s.get('windowBorderSize', 1))}
    col.active_border = {act_hypr}
    col.inactive_border = {inact_hypr}
}}

decoration {{
    rounding = {int(s.get('windowRounding', 15))}
    active_opacity = {float(s.get('windowOpacity', 0.95)):.2f}
    inactive_opacity = {float(s.get('inactiveOpacity', 0.90)):.2f}
    dim_inactive = {'true' if s.get('dimInactive', False) else 'false'}
    dim_strength = {float(s.get('dimStrength', 0.15)):.2f}

    blur {{
        enabled = {'true' if s.get('blurEnabled', True) else 'false'}
        size = {int(s.get('blurSize', 8))}
        passes = {int(s.get('blurPasses', 2))}
        xray = {'true' if s.get('blurXray', False) else 'false'}
        popups = {'true' if s.get('blurPopups', True) else 'false'}
        special = {'true' if s.get('blurSpecialWs', False) else 'false'}
    }}

    shadow {{
        enabled = {'true' if s.get('shadowEnabled', True) else 'false'}
        range = {int(s.get('shadowRange', 15))}
        render_power = {int(s.get('shadowRenderPower', 4))}
        color = {shadow_hypr}
    }}
}}

input {{
    sensitivity = {float(s.get('mouseSensitivity', 0.0)):.2f}
    accel_profile = {s.get('mouseAccelProfile', 'flat')}
    repeat_delay = {int(s.get('repeatDelay', 500))}
    repeat_rate = {int(s.get('repeatRate', 35))}

    touchpad {{
        disable_while_typing = {'true' if s.get('touchpadDisableTyping', True) else 'false'}
        natural_scroll = {'true' if s.get('touchpadNaturalScroll', True) else 'false'}
        scroll_factor = {float(s.get('touchpadScrollFactor', 0.3)):.2f}
    }}
}}

gestures {{
    workspace_swipe = true
    workspace_swipe_fingers = {int(s.get('workspaceSwipeFingers', 4))}
}}

animations {{
    enabled = {'true' if s.get('animationsEnabled', True) else 'false'}
}}
"""
                with open(HYPR_TWEAKER_CONF, "w") as f:
                    f.write(hypr_conf_content)
            except Exception as e:
                print(f"Notice: could not write {HYPR_TWEAKER_CONF}: {e}", file=sys.stderr)

            # 2. If Caelestia Shell configuration exists, persist to Lua variables and shell.json
            if os.path.isdir(CAELESTIA_CONF_DIR) or os.path.isfile(VARS_LUA):
                os.makedirs(CAELESTIA_CONF_DIR, exist_ok=True)
                with open(VARS_LUA, "w") as f:
                    f.write(lua_output)

                shell_json_path = os.path.expanduser("~/.config/caelestia/shell.json")
                if os.path.exists(shell_json_path):
                    try:
                        with open(shell_json_path, "r") as f:
                            sdata = json.load(f)
                        if "services" not in sdata:
                            sdata["services"] = {}
                        sdata["services"]["brightnessIncrement"] = round(float(s.get("brightnessStep", 5)) / 100.0, 4)
                        sdata["services"]["audioIncrement"] = round(float(s.get("volumeStep", 5)) / 100.0, 4)
                        with open(shell_json_path, "w") as f:
                            json.dump(sdata, f, indent=4)
                    except Exception:
                        pass

                update_shell_step_live("brightness", s.get("brightnessStep", 5))
                update_shell_step_live("audio", s.get("volumeStep", 5))

            # Sync foot terminal font if configured
            if "monospaceFont" in s:
                update_foot_font(s["monospaceFont"])

            # Invalidate Lua require cache in Hyprland's Lua VM so fresh configs are evaluated
            subprocess.run([
                "hyprctl", "eval",
                "package.loaded['hypr-vars'] = nil; package.loaded['variables'] = nil; package.loaded['hyprland/decoration'] = nil; package.loaded['hyprland.decoration'] = nil; package.loaded['hyprland/general'] = nil; package.loaded['hyprland.general'] = nil; package.loaded['hyprland/input'] = nil; package.loaded['hyprland.input'] = nil; package.loaded['hyprland/animations'] = nil; package.loaded['hyprland.animations'] = nil; package.loaded['hyprland/rules'] = nil; package.loaded['hyprland.rules'] = nil"
            ], check=False, stderr=subprocess.DEVNULL)

            # Reload Hyprland to lock in changes
            subprocess.run(["hyprctl", "reload"], check=False, stderr=subprocess.DEVNULL)

            # Re-apply live settings to compositor
            self._do_live_apply()

            toast = Adw.Toast.new("✓ Settings saved and applied successfully!")
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)
        except Exception as e:
            toast = Adw.Toast.new(f"Failed to save: {e}")
            self.toast_overlay.add_toast(toast)


class TweakerApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = TweakerWindow(self)
        win.present()


if __name__ == "__main__":
    app = TweakerApp()
    sys.exit(app.run(sys.argv))
