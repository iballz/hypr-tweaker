#!/usr/bin/env python3
"""
Hypr Tweaker - Intel PSR (Panel Self Refresh) Helper
Safely queries and toggles Panel Self Refresh (PSR) configuration for Intel iGPUs
via /etc/default/grub and /etc/modprobe.d/i915-psr.conf.
"""

import sys
import os
import re
import json
import shutil
import subprocess

GRUB_DEFAULT_FILE = "/etc/default/grub"
GRUB_BACKUP_FILE = "/etc/default/grub.hyprtweaker.bak"
MODPROBE_PSR_FILE = "/etc/modprobe.d/i915-psr.conf"
GRUB_CFG_FILE = "/boot/grub/grub.cfg"
GRUB_MKCONFIG_BIN = "/usr/bin/grub-mkconfig"

PSR_KERNEL_PARAMS = ["i915.enable_psr=0", "xe.enable_psr=0"]


def check_intel_gpu():
    """Detect if an Intel GPU is present on the system."""
    for i in range(8):
        vendor_path = f"/sys/class/drm/card{i}/device/vendor"
        if os.path.exists(vendor_path):
            try:
                with open(vendor_path, "r") as f:
                    if f.read().strip().lower() == "0x8086":
                        return True
            except Exception:
                pass
    return False


def is_running_disabled():
    """Check if PSR is disabled in current boot session via /proc/cmdline."""
    try:
        with open("/proc/cmdline", "r") as f:
            cmdline = f.read()
        return any(p in cmdline for p in PSR_KERNEL_PARAMS)
    except Exception:
        return False


def is_configured_disabled():
    """Check if PSR is set to be disabled in /etc/default/grub or /etc/modprobe.d/."""
    # Check /etc/default/grub
    if os.path.isfile(GRUB_DEFAULT_FILE):
        try:
            with open(GRUB_DEFAULT_FILE, "r") as f:
                content = f.read()
            match = re.search(r'^(GRUB_CMDLINE_LINUX_DEFAULT\s*=\s*)(["\'])(.*?)\2', content, flags=re.MULTILINE)
            if match:
                val = match.group(3)
                if any(p in val for p in PSR_KERNEL_PARAMS):
                    return True
        except Exception:
            pass

    # Check /etc/modprobe.d/i915-psr.conf
    if os.path.isfile(MODPROBE_PSR_FILE):
        try:
            with open(MODPROBE_PSR_FILE, "r") as f:
                content = f.read()
            if "enable_psr=0" in content:
                return True
        except Exception:
            pass

    return False


def get_status():
    has_intel = check_intel_gpu()
    running_dis = is_running_disabled()
    configured_dis = is_configured_disabled()

    # Reconcile status text
    if not has_intel:
        status_text = "No Intel graphics detected"
        state_key = "unsupported"
    elif configured_dis and running_dis:
        status_text = "Disabled (Active)"
        state_key = "disabled"
    elif configured_dis and not running_dis:
        status_text = "Disabled (Reboot required)"
        state_key = "disabled_pending_reboot"
    elif not configured_dis and running_dis:
        status_text = "Enabled (Reboot required)"
        state_key = "enabled_pending_reboot"
    else:
        status_text = "Enabled (Power-saving active)"
        state_key = "enabled"

    return {
        "has_intel": has_intel,
        "running_disabled": running_dis,
        "configured_disabled": configured_dis,
        "state_key": state_key,
        "status_text": status_text
    }


def modify_grub_content(content, enable_psr):
    """
    If enable_psr is True: removes PSR disable parameters.
    If enable_psr is False: adds PSR disable parameters.
    """
    def repl(m):
        prefix, quote, val = m.group(1), m.group(2), m.group(3)
        tokens = val.split()
        if enable_psr:
            # Remove PSR disable flags
            tokens = [t for t in tokens if not any(t.startswith(x) for x in ["i915.enable_psr=", "xe.enable_psr="])]
        else:
            # Add PSR disable flags
            for p in PSR_KERNEL_PARAMS:
                if p not in tokens:
                    tokens.append(p)
        return f"{prefix}{quote}{' '.join(tokens)}{quote}"

    return re.sub(
        r'^(GRUB_CMDLINE_LINUX_DEFAULT\s*=\s*)(["\'])(.*?)\2',
        repl,
        content,
        flags=re.MULTILINE
    )


def apply_psr(enable_psr):
    """Apply PSR setting (enable or disable). Must be run as root."""
    if os.geteuid() != 0:
        print("ERROR: Root privileges required. Run with pkexec.", file=sys.stderr)
        sys.exit(2)

    if not os.path.isfile(GRUB_DEFAULT_FILE):
        print(f"ERROR: {GRUB_DEFAULT_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    # 1. Read existing GRUB default file
    with open(GRUB_DEFAULT_FILE, "r") as f:
        original_grub = f.read()

    new_grub = modify_grub_content(original_grub, enable_psr=enable_psr)

    # Backup original GRUB config
    shutil.copy2(GRUB_DEFAULT_FILE, GRUB_BACKUP_FILE)

    # Write new GRUB default file
    with open(GRUB_DEFAULT_FILE, "w") as f:
        f.write(new_grub)

    # 2. Update modprobe config
    try:
        if enable_psr:
            if os.path.exists(MODPROBE_PSR_FILE):
                os.remove(MODPROBE_PSR_FILE)
        else:
            os.makedirs(os.path.dirname(MODPROBE_PSR_FILE), exist_ok=True)
            with open(MODPROBE_PSR_FILE, "w") as f:
                f.write(
                    "# Generated by Caelestia Hyprland Tweaker\n"
                    "# Disables Intel Panel Self Refresh to eliminate cursor/typing wake-up stutters\n"
                    "options i915 enable_psr=0\n"
                    "options xe enable_psr=0\n"
                )
    except Exception as e:
        print(f"WARNING: Could not update {MODPROBE_PSR_FILE}: {e}", file=sys.stderr)

    # 3. Regenerate GRUB config
    if os.path.isfile(GRUB_MKCONFIG_BIN) and os.path.isfile(GRUB_CFG_FILE):
        print("Running grub-mkconfig to update /boot/grub/grub.cfg...")
        env = os.environ.copy()
        env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:" + env.get("PATH", "")
        res = subprocess.run([GRUB_MKCONFIG_BIN, "-o", GRUB_CFG_FILE], capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"ERROR: grub-mkconfig failed:\n{res.stderr}", file=sys.stderr)
            # Restore backup
            shutil.copy2(GRUB_BACKUP_FILE, GRUB_DEFAULT_FILE)
            sys.exit(1)

    print(f"SUCCESS: PSR {'enabled' if enable_psr else 'disabled'} successfully.")
    sys.exit(0)


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "status":
        print(json.dumps(get_status(), indent=2))
        sys.exit(0)
    elif sys.argv[1] == "disable":
        apply_psr(enable_psr=False)
    elif sys.argv[1] == "enable":
        apply_psr(enable_psr=True)
    else:
        print(f"Usage: {sys.argv[0]} [status|disable|enable]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
