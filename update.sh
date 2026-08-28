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
USE_AUTO_VPN=0
TUNNEL_PID=""

cleanup_tunnel() {
    if [ -n "$TUNNEL_PID" ]; then
        kill "$TUNNEL_PID" 2>/dev/null || true
        wait "$TUNNEL_PID" 2>/dev/null || true
    fi
}
trap cleanup_tunnel EXIT INT TERM

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --proxy|-p)
            PROXY_URL="$2"
            shift 2
            ;;
        --vpn|--auto-vpn)
            USE_AUTO_VPN=1
            shift
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
            echo "  --proxy <URL>     Использовать HTTP/HTTPS/SOCKS5 прокси или ссылку на VPN-ноду (ss://, vless://, trojan://)"
            echo "  --vpn, --auto-vpn Автоматически найти рабочую VPN-ноду через Sentinel-Core и поднять локальный Sing-box туннель"
            echo "  --no-proxy        Игнорировать прокси из .env и окружения"
            echo "  --auto, -y        Автоматический режим обновления без интерактива"
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

# Function to check and launch VPN tunnel (specific node or auto-rotator)
try_start_vpn_tunnel() {
    local TARGET_NODE="$1"
    local PY_EXEC="python3"
    [ -x "bot/venv/bin/python3" ] && PY_EXEC="bot/venv/bin/python3"
    [ -x "bot/venv/bin/python" ] && PY_EXEC="bot/venv/bin/python"

    if ! command -v "$PY_EXEC" >/dev/null 2>&1; then
        return 1
    fi

    # Check for sentinel-core binary or library
    local CORE_FOUND=0
    if [ -x "bot/bin/sentinel-core" ] || [ -f "bot/bin/libsentinel-core.so" ] || command -v sentinel-core >/dev/null 2>&1; then
        CORE_FOUND=1
    fi

    # Check for proxy engine (Sing-box or Xray)
    local ENGINE_FOUND=0
    if [ -x "bot/bin/sing-box" ] || [ -x "bot/bin/xray" ] || command -v sing-box >/dev/null 2>&1 || command -v xray >/dev/null 2>&1; then
        ENGINE_FOUND=1
    fi

    if [ "$CORE_FOUND" -eq 1 ] && [ "$ENGINE_FOUND" -eq 1 ]; then
        local LOG_FILE="/tmp/proxy_rotator_update.$$"
        if [ -n "$TARGET_NODE" ]; then
            echo "[+] Запуск локального Sing-box туннеля для ноды ${TARGET_NODE%%:*}..."
            PYTHONPATH="${SCRIPT_DIR}/bot" "$PY_EXEC" -m core.proxy_rotator --node "$TARGET_NODE" --port 10818 > "$LOG_FILE" 2>&1 &
            TUNNEL_PID=$!
        else
            echo "[+] Обнаружены Sentinel-Core и Sing-box/Xray. Поиск рабочего VPN-соединения..."
            PYTHONPATH="${SCRIPT_DIR}/bot" "$PY_EXEC" -m core.proxy_rotator --find-and-start --port 10818 > "$LOG_FILE" 2>&1 &
            TUNNEL_PID=$!
        fi
        
        # Wait up to 10 seconds for tunnel to become ready
        local READY=0
        for i in {1..20}; do
            if grep -q "PROXY_READY" "$LOG_FILE" 2>/dev/null; then
                READY=1
                break
            fi
            if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
                break
            fi
            sleep 0.5
        done

        if [ "$READY" -eq 1 ]; then
            VALID_PROXY="socks5://127.0.0.1:10818"
            export http_proxy="$VALID_PROXY"
            export https_proxy="$VALID_PROXY"
            export all_proxy="$VALID_PROXY"
            export HTTP_PROXY="$VALID_PROXY"
            export HTTPS_PROXY="$VALID_PROXY"
            export ALL_PROXY="$VALID_PROXY"
            GIT_PROXY_OPTS=("-c" "http.proxy=$VALID_PROXY" "-c" "https.proxy=$VALID_PROXY")
            CORE_PROXY_ARG=("--proxy" "$VALID_PROXY")
            echo "[+] VPN-туннель успешно поднят на $VALID_PROXY!"
            rm -f "$LOG_FILE"
            return 0
        else
            echo "[-] Не удалось запустить VPN-туннель."
            cleanup_tunnel
            rm -f "$LOG_FILE"
            return 1
        fi
    fi
    return 1
}

VALID_PROXY=""
GIT_PROXY_OPTS=()
CORE_PROXY_ARG=()

# 1. Start VPN connection immediately if configured
if [ -n "$PROXY_URL" ] && [ "$NO_PROXY" -eq 0 ]; then
    if [[ "$PROXY_URL" =~ ^(http|https|socks4|socks5|socks5h):// ]]; then
        VALID_PROXY="$PROXY_URL"
        echo "[+] Настроено прямое подключение через HTTP/SOCKS прокси: $VALID_PROXY"
        export http_proxy="$VALID_PROXY"
        export https_proxy="$VALID_PROXY"
        export all_proxy="$VALID_PROXY"
        export HTTP_PROXY="$VALID_PROXY"
        export HTTPS_PROXY="$VALID_PROXY"
        export ALL_PROXY="$VALID_PROXY"
        GIT_PROXY_OPTS=("-c" "http.proxy=$VALID_PROXY" "-c" "https.proxy=$VALID_PROXY")
        CORE_PROXY_ARG=("--proxy" "$VALID_PROXY")
    elif [[ "$PROXY_URL" =~ ^(ss|vless|vmess|trojan|hy2|hysteria2|tuic|wireguard|wg):// ]]; then
        echo "[+] В конфигурации задана VPN-нода (${PROXY_URL%%:*}). Подключение к VPN..."
        if ! try_start_vpn_tunnel "$PROXY_URL"; then
            echo "[!] Прямое подключение к ноде не удалось. Поиск резервной рабочей ноды через ротатор..."
            try_start_vpn_tunnel "" || true
        fi
    fi
elif [ "$USE_AUTO_VPN" -eq 1 ]; then
    try_start_vpn_tunnel "" || true
fi

echo "===================================================="
echo "🔄 UPDATING PROXMOX LXC MONITOR BOT (CONTROLLER)"
echo "===================================================="

# 1. Pull latest updates from Git
echo "[+] Pulling latest updates from Git..."
OLD_HEAD=$(git rev-parse HEAD 2>/dev/null)

pull_git() {
    if [ -n "$VALID_PROXY" ]; then
        git -c "http.proxy=$VALID_PROXY" -c "https.proxy=$VALID_PROXY" fetch origin main && git reset --hard origin/main
    else
        git fetch origin main && git reset --hard origin/main
    fi
}

PULL_SUCCESS=0
if pull_git; then
    PULL_SUCCESS=1
else
    echo "[!] Прямое подключение к GitHub для git fetch не удалось. Пробуем через зеркало GitHub..."
    if git fetch "https://ghproxy.net/https://github.com/blackalex1/proxmox_Sentinel.git" main 2>/dev/null && git reset --hard FETCH_HEAD; then
        echo "[+] Git успешно обновлен через быстрое зеркало!"
        PULL_SUCCESS=1
    elif git fetch "https://gh-proxy.com/https://github.com/blackalex1/proxmox_Sentinel.git" main 2>/dev/null && git reset --hard FETCH_HEAD; then
        echo "[+] Git успешно обновлен через зеркало gh-proxy.com!"
        PULL_SUCCESS=1
    fi
fi

# If Git pull still failed, try starting Auto VPN
if [ "$PULL_SUCCESS" -eq 0 ] && [ -z "$TUNNEL_PID" ]; then
    if try_start_vpn_tunnel ""; then
        echo "[+] Повторная попытка git fetch через автоматический VPN-туннель..."
        pull_git && PULL_SUCCESS=1
    fi
fi

if [ "$PULL_SUCCESS" -eq 0 ] && [ -t 0 ] && [ "$AUTO_MODE" -eq 0 ]; then
    echo ""
    echo "===================================================="
    echo "🌐 НАСТРОЙКА ПОДКЛЮЧЕНИЯ К GITHUB (PROXY / VPN)"
    echo "===================================================="
    echo "GitHub недоступен напрямую. Укажите локальный HTTP или SOCKS5 прокси."
    read -p "Введите адрес прокси (например, http://127.0.0.1:7890 или socks5://127.0.0.1:1080) [Enter для пропуска]: " USER_PROXY
    if [ -n "$USER_PROXY" ]; then
        VALID_PROXY="$USER_PROXY"
        export http_proxy="$VALID_PROXY"
        export https_proxy="$VALID_PROXY"
        export all_proxy="$VALID_PROXY"
        export HTTP_PROXY="$VALID_PROXY"
        export HTTPS_PROXY="$VALID_PROXY"
        export ALL_PROXY="$VALID_PROXY"
        CORE_PROXY_ARG=("--proxy" "$VALID_PROXY")
        echo "[+] Повторная попытка git fetch через $VALID_PROXY..."
        pull_git && PULL_SUCCESS=1
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
        if "$UV_BIN" pip install --upgrade --python bot/venv -r bot/requirements.txt; then
            echo "[+] Python dependencies updated successfully using uv."
        else
            echo "[!] Failed to update Python dependencies with uv."
        fi
    else
        echo "[+] uv not found, checking for pip in virtual environment..."
        if [ -f "bot/venv/bin/pip" ]; then
            if bot/venv/bin/pip install --upgrade pip && bot/venv/bin/pip install --upgrade -r bot/requirements.txt; then
                echo "[+] Python dependencies updated successfully."
            else
                echo "[!] Failed to update Python dependencies."
            fi
        else
            echo "[+] pip not found in venv/bin. Trying python3 -m pip..."
            if bot/venv/bin/python3 -m pip install --upgrade pip 2>/dev/null || bot/venv/bin/python -m pip install --upgrade pip 2>/dev/null; then
                if bot/venv/bin/python3 -m pip install --upgrade -r bot/requirements.txt || bot/venv/bin/python -m pip install --upgrade -r bot/requirements.txt; then
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
