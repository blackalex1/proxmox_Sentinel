#!/usr/bin/env bash

# ==============================================================================
# Sing-box & Xray-Core Proxy Engine Downloader for Controller Bot
# Fetches official Sing-box (primary) and Xray-core binaries for current OS/Arch
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"
AUTO_MODE=0

for arg in "$@"; do
    case "$arg" in
        --auto|-y) AUTO_MODE=1 ;;
        -*) ;;
        *) BIN_DIR="$arg" ;;
    esac
done

mkdir -p "$BIN_DIR"

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

is_installed=0
if [ -x "$BIN_DIR/sing-box" ] || [ -f "$BIN_DIR/sing-box.exe" ] || [ -x "$BIN_DIR/xray" ] || [ -f "$BIN_DIR/xray.exe" ]; then
    is_installed=1
fi

echo "[+] Проверка наличия Sing-box / Xray-core в $BIN_DIR..."

fetch_singbox() {
    echo "[+] Загрузка Sing-box из официального репозитория SagerNet/sing-box..."
    local SB_TAG=""
    if command -v python3 &>/dev/null; then
        SB_TAG=$(python3 -c "
import urllib.request, json
try:
    req = urllib.request.Request('https://api.github.com/repos/SagerNet/sing-box/releases/latest', headers={'User-Agent': 'SentinelController'})
    with urllib.request.urlopen(req, timeout=5) as r:
        print(json.loads(r.read().decode('utf-8'))['tag_name'])
except Exception:
    pass
" 2>/dev/null)
    fi

    if [ -z "$SB_TAG" ]; then
        SB_TAG="v1.11.4"
    fi
    local VER_NUM="${SB_TAG#v}"

    local SB_URL=""
    if [ "$OS" = "windows" ]; then
        SB_URL="https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/sing-box-${VER_NUM}-windows-${ARCH_SINGBOX}.zip"
    elif [ "$OS" = "macos" ]; then
        SB_URL="https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/sing-box-${VER_NUM}-darwin-${ARCH_SINGBOX}.tar.gz"
    else
        SB_URL="https://github.com/SagerNet/sing-box/releases/download/${SB_TAG}/sing-box-${VER_NUM}-linux-${ARCH_SINGBOX}.tar.gz"
    fi

    local TMP_ARCHIVE="/tmp/singbox_latest.tar.gz"
    if [[ "$SB_URL" == *.zip ]]; then
        TMP_ARCHIVE="/tmp/singbox_latest.zip"
    fi

    if curl -fsSL --connect-timeout 10 -o "$TMP_ARCHIVE" "$SB_URL"; then
        if [[ "$TMP_ARCHIVE" == *.tar.gz ]]; then
            tar -xzf "$TMP_ARCHIVE" --strip-components=1 -C "$BIN_DIR" 2>/dev/null || tar -xzf "$TMP_ARCHIVE" -C "$BIN_DIR"
        elif command -v unzip &>/dev/null; then
            unzip -q -o "$TMP_ARCHIVE" -d "/tmp/sb_extract" 2>/dev/null && cp /tmp/sb_extract/*/sing-box* "$BIN_DIR/" 2>/dev/null && rm -rf /tmp/sb_extract
        elif command -v python3 &>/dev/null; then
            python3 -c "import zipfile; zipfile.ZipFile('$TMP_ARCHIVE').extractall('$BIN_DIR')"
        fi
        chmod +x "$BIN_DIR/sing-box" 2>/dev/null || true
        rm -f "$TMP_ARCHIVE"
        echo "✓ Sing-box успешно установлен в $BIN_DIR"
        return 0
    fi
    return 1
}

fetch_xray() {
    echo "[+] Загрузка Xray-core из официального репозитория XTLS/Xray-core..."
    local XRAY_URL=""
    if [ "$OS" = "windows" ]; then
        XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-windows-${ARCH_XRAY}.zip"
    elif [ "$OS" = "macos" ]; then
        XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-macos-${ARCH_XRAY}.zip"
    else
        XRAY_URL="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-${ARCH_XRAY}.zip"
    fi

    local TMP_ZIP="/tmp/xray_latest.zip"
    if [ "$OS" = "windows" ]; then
        TMP_ZIP="$BIN_DIR/xray_temp.zip"
    fi

    if curl -fsSL --connect-timeout 10 -o "$TMP_ZIP" "$XRAY_URL"; then
        if command -v unzip &>/dev/null; then
            unzip -q -o "$TMP_ZIP" -d "$BIN_DIR" xray xray.exe geoip.dat geosite.dat 2>/dev/null || unzip -q -o "$TMP_ZIP" -d "$BIN_DIR"
            chmod +x "$BIN_DIR/xray" 2>/dev/null || true
            rm -f "$TMP_ZIP"
            echo "✓ Xray-core успешно установлен в $BIN_DIR"
            return 0
        elif command -v python3 &>/dev/null; then
            python3 -c "import zipfile; zipfile.ZipFile('$TMP_ZIP').extractall('$BIN_DIR')"
            chmod +x "$BIN_DIR/xray" 2>/dev/null || true
            rm -f "$TMP_ZIP"
            echo "✓ Xray-core успешно распакован через Python в $BIN_DIR"
            return 0
        fi
    fi
    echo "⚠️ Не удалось загрузить Xray-core напрямую"
    return 1
}

# Download Sing-box (Primary for resource efficiency) and Xray-core (Fallback)
fetch_singbox || true
fetch_xray || true

if [ -x "$BIN_DIR/sing-box" ] || [ -f "$BIN_DIR/sing-box.exe" ] || [ -x "$BIN_DIR/xray" ] || [ -f "$BIN_DIR/xray.exe" ]; then
    echo "✓ Proxy ядра готовы к работе в $BIN_DIR"
else
    echo "⚠️ Не удалось загрузить Xray/Sing-box ядра. Будет использоваться прямой SOCKS5/HTTP fallback."
fi
