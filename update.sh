#!/usr/bin/env bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root (use sudo)"
  exit 1
fi

# Navigate to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROXY_URL=""
NO_PROXY=0
AUTO_MODE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --proxy|-p)
            PROXY_URL="$2"
            shift 2
            ;;
        --no-proxy)
            NO_PROXY=1
            shift
            ;;
        --auto|-y)
            AUTO_MODE=1
            shift
            ;;
        --help|-h)
            echo "Использование: sudo ./update.sh [опции]"
            echo "Опции:"
            echo "  --proxy <URL>   Использовать HTTP/HTTPS/SOCKS5 прокси (например, http://127.0.0.1:7890 или socks5://127.0.0.1:1080)"
            echo "  --no-proxy      Игнорировать прокси из .env и окружения"
            echo "  --auto, -y      Автоматический режим обновления без интерактива"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Check PROXY_URL from .env if not specified via CLI
if [ -z "$PROXY_URL" ] && [ "$NO_PROXY" -eq 0 ]; then
    for env_file in "bot/config/.env" ".env"; do
        if [ -f "$env_file" ]; then
            ENV_P=$(grep -E '^[[:space:]]*PROXY_URL=' "$env_file" 2>/dev/null | cut -d'=' -f2- | tr -d '"'\'' ')
            if [ -n "$ENV_P" ]; then
                PROXY_URL="$ENV_P"
                break
            fi
        fi
    done
    if [ -z "$PROXY_URL" ]; then
        PROXY_URL="${HTTPS_PROXY:-${HTTP_PROXY:-${ALL_PROXY:-${https_proxy:-${http_proxy:-${all_proxy:-}}}}}}"
    fi
fi

# Apply proxy settings if available
GIT_PROXY_OPTS=()
CORE_PROXY_ARG=()
if [ -n "$PROXY_URL" ] && [ "$NO_PROXY" -eq 0 ]; then
    echo "[+] Настроено подключение через прокси / VPN: $PROXY_URL"
    export http_proxy="$PROXY_URL"
    export https_proxy="$PROXY_URL"
    export all_proxy="$PROXY_URL"
    export HTTP_PROXY="$PROXY_URL"
    export HTTPS_PROXY="$PROXY_URL"
    export ALL_PROXY="$PROXY_URL"
    GIT_PROXY_OPTS=("-c" "http.proxy=$PROXY_URL" "-c" "https.proxy=$PROXY_URL")
    CORE_PROXY_ARG=("--proxy" "$PROXY_URL")
fi

echo "===================================================="
echo "🔄 UPDATING PROXMOX LXC MONITOR BOT (CONTROLLER)"
echo "===================================================="

# 1. Pull latest updates from Git
echo "[+] Pulling latest updates from Git..."
OLD_HEAD=$(git rev-parse HEAD 2>/dev/null)

pull_git() {
    git "${GIT_PROXY_OPTS[@]}" fetch origin main && git reset --hard origin/main
}

if ! pull_git; then
    echo "[!] Не удалось выполнить git fetch напрямую."
    if [ -t 0 ] && [ "$AUTO_MODE" -eq 0 ]; then
        echo ""
        echo "===================================================="
        echo "🌐 НАСТРОЙКА ПОДКЛЮЧЕНИЯ К GITHUB (PROXY / VPN)"
        echo "===================================================="
        echo "Возможно, GitHub заблокирован провайдером или недоступен напрямую."
        read -p "Введите адрес прокси/VPN (например, http://127.0.0.1:7890 или socks5://127.0.0.1:1080) [Enter для пропуска]: " USER_PROXY
        if [ -n "$USER_PROXY" ]; then
            PROXY_URL="$USER_PROXY"
            export http_proxy="$PROXY_URL"
            export https_proxy="$PROXY_URL"
            export all_proxy="$PROXY_URL"
            export HTTP_PROXY="$PROXY_URL"
            export HTTPS_PROXY="$PROXY_URL"
            export ALL_PROXY="$PROXY_URL"
            GIT_PROXY_OPTS=("-c" "http.proxy=$PROXY_URL" "-c" "https.proxy=$PROXY_URL")
            CORE_PROXY_ARG=("--proxy" "$PROXY_URL")
            echo "[+] Повторная попытка git fetch через $PROXY_URL..."
            pull_git || echo "[!] Ошибка: Не удалось обновить Git репозиторий даже через указанный прокси."
        fi
    fi
fi

NEW_HEAD=$(git rev-parse HEAD 2>/dev/null)
if [ "$OLD_HEAD" != "$NEW_HEAD" ] && [ -n "$OLD_HEAD" ]; then
    echo "[+] Changes pulled:"
    git diff --stat "$OLD_HEAD" "$NEW_HEAD"
else
    echo "[+] Already up to date."
fi
echo "[+] Git update step completed."

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

# 3. Update sentinel-core security engine
echo "[+] Checking and updating sentinel-core engine..."
if [ -f "bot/fetch_core.sh" ]; then
    chmod +x "bot/fetch_core.sh"
    FETCH_ARGS=("${CORE_PROXY_ARG[@]}")
    [ "$AUTO_MODE" -eq 1 ] && FETCH_ARGS+=("--auto")
    bash "bot/fetch_core.sh" "${FETCH_ARGS[@]}"
else
    echo "[!] bot/fetch_core.sh not found. Skipping core update."
fi

# 3.5 Update proxy engines (Sing-box / Xray-core)
echo "[+] Checking and updating proxy engines (Sing-box / Xray-core)..."
if [ -f "bot/fetch_proxy_core.sh" ]; then
    chmod +x "bot/fetch_proxy_core.sh"
    FETCH_PROXY_ARGS=("${CORE_PROXY_ARG[@]}")
    [ "$AUTO_MODE" -eq 1 ] && FETCH_PROXY_ARGS+=("--auto")
    bash "bot/fetch_proxy_core.sh" "${FETCH_PROXY_ARGS[@]}"
fi

# 4. Restart proxmox-lxc-bot service
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
