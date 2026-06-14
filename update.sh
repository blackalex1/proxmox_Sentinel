#!/usr/bin/env bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root (use sudo)"
  exit 1
fi

# Navigate to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "===================================================="
echo "🔄 UPDATING PROXMOX LXC MONITOR BOT (CONTROLLER)"
echo "===================================================="

# 1. Pull latest updates from Git
echo "[+] Pulling latest updates from Git..."
if git pull; then
    echo "[+] Git pull completed successfully."
else
    echo "[!] Git pull failed. If you have local changes, stash them or resolve conflicts."
fi

# 2. Update Python virtual environment dependencies
echo "[+] Updating Python dependencies..."
if [ -f "bot/requirements.txt" ] && [ -d "bot/venv" ]; then
    if bot/venv/bin/pip install --upgrade pip && bot/venv/bin/pip install -r bot/requirements.txt; then
        echo "[+] Python dependencies updated successfully."
    else
        echo "[!] Failed to update Python dependencies."
    fi
else
    echo "[!] Virtual environment or requirements.txt not found. Skipping pip install."
fi

# 3. Restart proxmox-lxc-bot service
echo "[+] Restarting proxmox-lxc-bot system service..."
if systemctl is-active --quiet proxmox-lxc-bot; then
    systemctl restart proxmox-lxc-bot
    echo "[+] proxmox-lxc-bot service restarted successfully!"
else
    if [ -f "/etc/systemd/system/proxmox-lxc-bot.service" ]; then
        systemctl daemon-reload
        systemctl enable proxmox-lxc-bot
        systemctl start proxmox-lxc-bot
        echo "[+] proxmox-lxc-bot service enabled and started!"
    else
        echo "[!] proxmox-lxc-bot service is not installed on this host."
    fi
fi

echo "===================================================="
echo "[+] Update process complete! Showing logs for proxmox-lxc-bot (Ctrl+C to exit)..."
echo "===================================================="
journalctl -u proxmox-lxc-bot -f -n 20
