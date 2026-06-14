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
    # Find uv binary
    UV_BIN="uv"
    if [ -f "${HOME}/.local/bin/uv" ]; then
        UV_BIN="${HOME}/.local/bin/uv"
    elif [ -f "/root/.local/bin/uv" ]; then
        UV_BIN="/root/.local/bin/uv"
    fi

    if command -v "$UV_BIN" >/dev/null 2>&1; then
        echo "[+] Found uv, updating dependencies using uv..."
        if "$UV_BIN" pip install --python bot/venv -r bot/requirements.txt; then
            echo "[+] Python dependencies updated successfully using uv."
        else
            echo "[!] Failed to update Python dependencies with uv."
        fi
    else
        echo "[+] uv not found, checking for pip in virtual environment..."
        if [ -f "bot/venv/bin/pip" ]; then
            if bot/venv/bin/pip install --upgrade pip && bot/venv/bin/pip install -r bot/requirements.txt; then
                echo "[+] Python dependencies updated successfully."
            else
                echo "[!] Failed to update Python dependencies."
            fi
        else
            echo "[+] pip not found in venv/bin. Trying python3 -m pip..."
            if bot/venv/bin/python3 -m pip install --upgrade pip 2>/dev/null || bot/venv/bin/python -m pip install --upgrade pip 2>/dev/null; then
                if bot/venv/bin/python3 -m pip install -r bot/requirements.txt || bot/venv/bin/python -m pip install -r bot/requirements.txt; then
                    echo "[+] Python dependencies updated successfully."
                else
                    echo "[!] Failed to update Python dependencies."
                fi
            else
                echo "[!] Neither uv nor pip was found. Trying to bootstrap pip..."
                if bot/venv/bin/python3 -m ensurepip 2>/dev/null || bot/venv/bin/python -m ensurepip 2>/dev/null; then
                    if bot/venv/bin/pip install --upgrade pip && bot/venv/bin/pip install -r bot/requirements.txt; then
                        echo "[+] Python dependencies updated successfully."
                    else
                        echo "[!] Failed to update Python dependencies."
                    fi
                else
                    echo "[!] Failed to update Python dependencies. Please install uv or pip."
                fi
            fi
        fi
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
