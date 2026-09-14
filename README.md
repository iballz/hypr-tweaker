# Hypr Tweaker 🎛️

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GTK4](https://img.shields.io/badge/GUI-GTK4%20%2F%20Libadwaita-indigo.svg)](https://gitlab.gnome.org/GNOME/libadwaita)
[![Compositor](https://img.shields.io/badge/Compositor-Hyprland-brightgreen.svg)](https://hyprland.org)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org)

**Hypr Tweaker** is a sleek, modern visual configurator and live tweaker for the **[Hyprland](https://hyprland.org)** Wayland compositor. Built with **Libadwaita** and **GTK4**, it provides an intuitive, real-time GUI to fine-tune your desktop appearance, animations, gestures, and hardware settings without manually hunting through config files.

---

## ✨ Features

- ⚡ **Instant Live Preview**: Adjust gaps, rounding, opacity, blur, and input settings in real-time with zero restart required (`hyprctl` debounced engine).
- 🪟 **Window Geometry & Gaps**:
  - Inner and outer window margins
  - Curved corner rounding radius
  - Active and inactive window borders (with toggle to completely remove borders)
  - Focused / background window opacities & inactive dimming
- 💧 **Blur & Glass Effects**:
  - Blur radius and multi-pass sampling (Kawase blur)
  - Context menu and dropdown surface blurring
  - Special scratchpad workspace blurring
  - X-Ray mode
- 🎨 **Color & Palette Controls**:
  - Color swatches for popular palettes (Caelestia Dynamic, Cyan, Catppuccin, Nord, Tokyo Night, Gruvbox)
  - Full-color RGBA color pickers for active/inactive borders and ambient drop shadows
- 🔤 **Typography & Cursor**:
  - Live system interface and monospace font pickers (auto-syncs with foot terminal)
  - Cursor theme selector and live pixel size adjustments
- 👆 **Touchpad & Gestures**:
  - Multi-touch swipe finger configuration (3 or 4 fingers)
  - Natural scrolling & scroll factor multiplier
  - Pointer sensitivity and acceleration profiles (`flat` / `adaptive`)
- 🔋 **Hardware & Performance**:
  - Dynamic GPU renderer detection (Intel, AMD, NVIDIA)
  - Intel Panel Self Refresh (PSR) toggle to eliminate micro-stuttering and typing lag
- 🔄 **Universal Compatibility**:
  - Seamlessly integrates with **Caelestia Shell** (`hypr-vars.lua` and `shell.json`).
  - Automatically writes standard Hyprland syntax (`~/.config/hypr/hypr-tweaker.conf`) for **any vanilla Hyprland install**.

---

## 🚀 Installation

### Option 1: One-Line Installer (Recommended)

Clone the repository and run the installer script:

```bash
git clone https://github.com/iballz/hypr-tweaker.git
cd hypr-tweaker
./install.sh
```

> **Note**: Running `./install.sh` installs the application to your user directory (`~/.local/bin` and `~/.local/share`). To install system-wide for all users, run `sudo ./install.sh`.

### Option 2: Arch Linux / AUR (PKGBUILD)

A `PKGBUILD` is included in the repository. You can build and install it locally:

```bash
git clone https://github.com/iballz/hypr-tweaker.git
cd hypr-tweaker
makepkg -si
```

*(AUR package `hypr-tweaker-git` coming soon)*

### Option 3: Run Standalone (No Install Required)

You can run Hypr Tweaker directly without installing:

```bash
git clone https://github.com/iballz/hypr-tweaker.git
cd hypr-tweaker
./bin/hypr-tweaker
```

---

## 📦 Dependencies

Ensure the following packages are installed on your distribution:

- `python` (>= 3.9)
- `python-gobject` (PyGObject)
- `gtk4`
- `libadwaita`
- `hyprland`
- `polkit` *(optional, required only for Intel PSR toggle)*

On **Arch Linux / EndeavourOS**:
```bash
sudo pacman -S python python-gobject gtk4 libadwaita hyprland
```

On **Fedora**:
```bash
sudo dnf install python3 python3-gobject gtk4 libadwaita hyprland
```

---

## 🛠️ Usage & Configuration

Once installed, launch **Hypr Tweaker** from your application launcher (Rofi, Wofi, Caelestia) or via terminal:

```bash
hypr-tweaker
```

### Saving Settings

- Click **Save and Apply** (or press <kbd>Ctrl</kbd> + <kbd>S</kbd>) in the header bar.
- **For Caelestia Shell users**: Changes are saved automatically to `~/.config/caelestia/hypr-vars.lua` and synced live via IPC.
- **For Standard / Vanilla Hyprland users**: Changes are saved to `~/.config/hypr/hypr-tweaker.conf`. To persist these settings on boot, add the following line to your `~/.config/hypr/hyprland.conf`:
  ```ini
  source = ~/.config/hypr/hypr-tweaker.conf
  ```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>S</kbd> | Save settings permanently |
| <kbd>Ctrl</kbd> + <kbd>Q</kbd> | Quit application |

---

## 🗑️ Uninstallation

To remove Hypr Tweaker, simply run the included uninstaller:

```bash
cd hypr-tweaker
./uninstall.sh
```

---

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).
