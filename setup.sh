#!/usr/bin/env bash

# ==============================================================================
# Proxmox Sentinel Controller - Master Setup Script
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/bot/setup.sh" ]; then
    chmod +x "$SCRIPT_DIR/bot/setup.sh"
    exec bash "$SCRIPT_DIR/bot/setup.sh" "$@"
else
    echo "[!] Error: bot/setup.sh not found in $SCRIPT_DIR."
    exit 1
fi
