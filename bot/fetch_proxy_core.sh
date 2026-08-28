#!/usr/bin/env bash

# ==============================================================================
# Sing-box & Xray-Core Proxy Engine Downloader for Controller Bot
# Fetches official Sing-box (primary) and Xray-core binaries for current OS/Arch
# Supports HTTP/HTTPS/SOCKS5 Proxies, VPN, and GitHub Fast Mirrors
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
AUTO_MODE=0
PROXY_URL=""

# Colors for interactive UI
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto|-y)
            AUTO_MODE=1
            shift
            ;;
        --proxy|-p)
            PROXY_URL="$2"
            shift 2
            ;;
        -*)
            shift
            ;;
        *)
            BIN_DIR="$1"
            shift
            ;;
    esac
done

mkdir -p "$BIN_DIR"

# Check PROXY_URL from .env if not set via CLI
if [ -z "$PROXY_URL" ]; then
    for env_file in "$SCRIPT_DIR/config/.env" "$SCRIPT_DIR/../bot/config/.env" "$SCRIPT_DIR/../.env" ".env"; do
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

VALID_PROXY=""
CURL_OPTS=("-fsSL" "--connect-timeout" "8" "--max-time" "30" "--speed-limit" "1024" "--speed-time" "6" "--retry" "1")

if [ -n "$PROXY_URL" ]; then
    if [[ "$PROXY_URL" =~ ^(http|https|socks4|socks5|socks5h):// ]]; then
        VALID_PROXY="$PROXY_URL"
        echo -e "${CYAN}[+] Использование прокси для Sing-box & Xray: $VALID_PROXY${NC}"
        export http_proxy="$VALID_PROXY"
        export https_proxy="$VALID_PROXY"
        export all_proxy="$VALID_PROXY"
        export HTTP_PROXY="$VALID_PROXY"
        export HTTPS_PROXY="$VALID_PROXY"
        export ALL_PROXY="$VALID_PROXY"
        CURL_OPTS+=("-x" "$VALID_PROXY")
    fi
fi

# 1. Detect OS
OS_TYPE="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS_TYPE" in
    linux*)   OS="linux" ;;
    darwin*)  OS="macos" ;;
    msys*|mingw*|cygwin*) OS="windows" ;;
    *)        OS="linux" ;;
esac

# 2. Detect Architecture
ARCH_RAW="$(uname -m | tr '[:upper:]' '[:lower:]')"
case "$ARCH_RAW" in
    x86_64|amd64)   ARCH_SINGBOX="amd64"; ARCH_XRAY="64" ;;
    aarch64|arm64)  ARCH_SINGBOX="arm64"; ARCH_XRAY="arm64-v8a" ;;
    armv7*|armhf)   ARCH_SINGBOX="armv7"; ARCH_XRAY="arm32-v7a" ;;
    *)              ARCH_SINGBOX="amd64"; ARCH_XRAY="64" ;;
esac

# 3. Detect current installed versions
SB_INSTALLED="Не установлено"
if [ -x "$BIN_DIR/sing-box" ] || [ -f "$BIN_DIR/sing-box.exe" ]; then
    SB_EXEC="$BIN_DIR/sing-box"
    [ -f "$BIN_DIR/sing-box.exe" ] && SB_EXEC="$BIN_DIR/sing-box.exe"
    SB_VER=$("$SB_EXEC" version 2>/dev/null | head -n 1 | awk '{print $3}' || true)
    if [ -n "$SB_VER" ]; then
        SB_INSTALLED="Установлено (${SB_VER})"
    else
        SB_INSTALLED="Установлено"
    fi
fi

XRAY_INSTALLED="Не установлено"
if [ -x "$BIN_DIR/xray" ] || [ -f "$BIN_DIR/xray.exe" ]; then
    XRAY_EXEC="$BIN_DIR/xray"
    [ -f "$BIN_DIR/xray.exe" ] && XRAY_EXEC="$BIN_DIR/xray.exe"
    XRAY_VER=$("$XRAY_EXEC" version 2>/dev/null | head -n 1 | awk '{print $2}' || true)
    if [ -n "$XRAY_VER" ]; then
        XRAY_INSTALLED="Установлено (${XRAY_VER})"
    else
        XRAY_INSTALLED="Установлено"
    fi
fi

fetch_singbox() {
    echo -e "${CYAN}[+] Загрузка Sing-box из официального репозитория SagerNet/sing-box...${NC}"
    local SB_TAG=""
    if command -v python3 &>/dev/null; then
        SB_TAG=$(python3 -c "
import urllib.request, json, os
urls = [
    'https://api.github.com/repos/SagerNet/sing-box/releases/latest',
    'https://ghproxy.net/https://api.github.com/repos/SagerNet/sing-box/releases/latest',
    'https://gh-proxy.com/https://api.github.com/repos/SagerNet/sing-box/releases/latest'
]
proxy = '$VALID_PROXY'
handlers = [urllib.request.ProxyHandler({'http': proxy, 'https': proxy})] if proxy else []
opener = urllib.request.build_opener(*handlers)
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'SentinelController'})
        with opener.open(req, timeout=6) as r:
            tag = json.loads(r.read().decode('utf-8'))['tag_name']
            if tag:
                print(tag)
                exit(0)
    except Exception:
        continue
" 2>/dev/null)
    fi

    if [ -z "$SB_TAG" ]; then
        SB_TAG="v1.11.4"
    fi
    local VER_NUM="${SB_TAG#v}"

    local SB_FILENAME=""
    if [ "$OS" = "windows" ]; then
        SB_FILENAME="sing-box-${VER_NUM}-windows-${ARCH_SINGBOX}.zip"
    elif [ "$OS" = "macos" ]; then
        SB_FILENAME="sing-box-${VER_NUM}-darwin-${ARCH_SINGBOX}.tar.gz"
    else
        SB_FILENAME="sing-box-${VER_NUM}-linux-${ARCH_SINGBOX}.tar.gz"
    fi

    local SB_CANDIDATES=(
        "https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/${SB_FILENAME}"
        "https://ghproxy.net/https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/${SB_FILENAME}"
        "https://gh-proxy.com/https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/${SB_FILENAME}"
        "https://mirror.ghproxy.com/https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/${SB_FILENAME}"
    )

    local TMP_ARCHIVE="/tmp/singbox_latest.tar.gz"
    if [[ "$SB_FILENAME" == *.zip ]]; then
        TMP_ARCHIVE="/tmp/singbox_latest.zip"
    fi

    for URL in "${SB_CANDIDATES[@]}"; do
        rm -f "$TMP_ARCHIVE"
        if curl "${CURL_OPTS[@]}" -o "$TMP_ARCHIVE" "$URL" 2>/dev/null; then
            if [ -s "$TMP_ARCHIVE" ] && ! head -n 1 "$TMP_ARCHIVE" | grep -iqE "<!DOCTYPE|<html|404: Not Found|\{\"message\":"; then
                if [[ "$TMP_ARCHIVE" == *.tar.gz ]]; then
                    tar -xzf "$TMP_ARCHIVE" --strip-components=1 -C "$BIN_DIR" 2>/dev/null || tar -xzf "$TMP_ARCHIVE" -C "$BIN_DIR"
                elif command -v unzip &>/dev/null; then
                    unzip -q -o "$TMP_ARCHIVE" -d "/tmp/sb_extract" 2>/dev/null && cp /tmp/sb_extract/*/sing-box* "$BIN_DIR/" 2>/dev/null && rm -rf /tmp/sb_extract
                elif command -v python3 &>/dev/null; then
                    python3 -c "import zipfile; zipfile.ZipFile('$TMP_ARCHIVE').extractall('$BIN_DIR')"
                fi
                chmod +x "$BIN_DIR/sing-box" 2>/dev/null || true
                rm -f "$TMP_ARCHIVE"
                echo -e "${GREEN}✓ Sing-box успешно установлен в $BIN_DIR${NC}"
                return 0
            fi
        fi
    done

    echo -e "${RED}⚠️ Не удалось загрузить Sing-box${NC}"
    return 1
}

fetch_xray() {
    echo -e "${CYAN}[+] Загрузка Xray-core из официального репозитория XTLS/Xray-core...${NC}"
    local XRAY_FILENAME=""
    if [ "$OS" = "windows" ]; then
        XRAY_FILENAME="Xray-windows-${ARCH_XRAY}.zip"
    elif [ "$OS" = "macos" ]; then
        XRAY_FILENAME="Xray-macos-${ARCH_XRAY}.zip"
    else
        XRAY_FILENAME="Xray-linux-${ARCH_XRAY}.zip"
    fi

    local XRAY_CANDIDATES=(
        "https://github.com/XTLS/Xray-core/releases/latest/download/${XRAY_FILENAME}"
        "https://ghproxy.net/https://github.com/XTLS/Xray-core/releases/latest/download/${XRAY_FILENAME}"
        "https://gh-proxy.com/https://github.com/XTLS/Xray-core/releases/latest/download/${XRAY_FILENAME}"
        "https://mirror.ghproxy.com/https://github.com/XTLS/Xray-core/releases/latest/download/${XRAY_FILENAME}"
    )

    local TMP_ZIP="/tmp/xray_latest.zip"
    if [ "$OS" = "windows" ]; then
        TMP_ZIP="$BIN_DIR/xray_temp.zip"
    fi

    for URL in "${XRAY_CANDIDATES[@]}"; do
        rm -f "$TMP_ZIP"
        if curl "${CURL_OPTS[@]}" -o "$TMP_ZIP" "$URL" 2>/dev/null; then
            if [ -s "$TMP_ZIP" ] && ! head -n 1 "$TMP_ZIP" | grep -iqE "<!DOCTYPE|<html|404: Not Found|\{\"message\":"; then
                if command -v unzip &>/dev/null; then
                    unzip -q -o "$TMP_ZIP" -d "$BIN_DIR" xray xray.exe geoip.dat geosite.dat 2>/dev/null || unzip -q -o "$TMP_ZIP" -d "$BIN_DIR"
                    chmod +x "$BIN_DIR/xray" 2>/dev/null || true
                    rm -f "$TMP_ZIP"
                    echo -e "${GREEN}✓ Xray-core успешно установлен в $BIN_DIR${NC}"
                    return 0
                elif command -v python3 &>/dev/null; then
                    python3 -c "import zipfile; zipfile.ZipFile('$TMP_ZIP').extractall('$BIN_DIR')"
                    chmod +x "$BIN_DIR/xray" 2>/dev/null || true
                    rm -f "$TMP_ZIP"
                    echo -e "${GREEN}✓ Xray-core успешно распакован в $BIN_DIR${NC}"
                    return 0
                fi
            fi
        fi
    done

    echo -e "${RED}⚠️ Не удалось загрузить Xray-core напрямую${NC}"
    return 1
}

if [ "$AUTO_MODE" -eq 1 ]; then
    # In auto mode, ensure at least Sing-box is installed
    if [ "$SB_INSTALLED" = "Не установлено" ]; then
        fetch_singbox || true
    fi
else
    # Interactive menu
    DEFAULT_PROXY_CHOICE="1"
    if [ "$SB_INSTALLED" != "Не установлено" ] || [ "$XRAY_INSTALLED" != "Не установлено" ]; then
        DEFAULT_PROXY_CHOICE="4"
    fi

    echo ""
    echo -e "${CYAN}====================================================${NC}"
    echo -e "${BLUE}🚀  ВЫБОР PROXY / VPN ДВИЖКА ДЛЯ FAILOVER МОСТА${NC}"
    echo -e "${CYAN}====================================================${NC}"
    echo -e "📌 Текущее состояние:"
    echo -e "  • ${YELLOW}Sing-box:${NC}  $SB_INSTALLED"
    echo -e "  • ${YELLOW}Xray-core:${NC} $XRAY_INSTALLED"
    echo -e "${CYAN}====================================================${NC}"
    echo -e "Варианты установки:"
    echo -e "  1) ${GREEN}🟢 Установить / Обновить Sing-box (Рекомендуется)${NC}"
    echo -e "  2) ${GREEN}🟢 Установить / Обновить Xray-core${NC}"
    echo -e "  3) 🌐 Установить оба движка (Sing-box + Xray-core)"
    echo -e "  4) ⏹️  Оставить текущие версии (Пропустить обновление)"
    read -t 15 -p "Выберите вариант [1-4] (по умолчанию $DEFAULT_PROXY_CHOICE): " PROXY_CHOICE || PROXY_CHOICE="$DEFAULT_PROXY_CHOICE"
    PROXY_CHOICE="${PROXY_CHOICE:-$DEFAULT_PROXY_CHOICE}"

    case "$PROXY_CHOICE" in
        1) fetch_singbox ;;
        2) fetch_xray ;;
        3) fetch_singbox; fetch_xray ;;
        4) echo -e "${GREEN}[+] Обновление прокси-движков пропущено.${NC}" ;;
        *) [ "$DEFAULT_PROXY_CHOICE" = "4" ] && echo -e "${GREEN}[+] Обновление прокси-движков пропущено.${NC}" || fetch_singbox ;;
    esac
fi

exit 0
