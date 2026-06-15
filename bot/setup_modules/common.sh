#!/usr/bin/env bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo_lang() {
    if [ "${INSTALL_LANG}" = "ru" ]; then
        echo -e -n "$1"
    else
        echo -e -n "$2"
    fi
}

print_lang() {
    if [ "${INSTALL_LANG}" = "ru" ]; then
        echo -e "$1"
    else
        echo -e "$2"
    fi
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Error: This script must be run as ROOT (sudo) / Этот скрипт должен быть запущен с правами ROOT (sudo).${NC}"
        echo -e "Please run as / Пожалуйста, запустите как: ${YELLOW}sudo ./setup.sh${NC}"
        exit 1
    fi
}

# Display welcome banner
show_welcome_banner() {
    print_lang "${BLUE}=== Proxmox LXC Monitor Bot - Полная автоматическая настройка ===${NC}" "${BLUE}=== Proxmox LXC Monitor Bot - Fully Automated Setup ===${NC}"
    print_lang "Директория установки: ${GREEN}${SCRIPT_DIR}${NC}" "Installation directory: ${GREEN}${SCRIPT_DIR}${NC}"
}

# Ask for installation proxy or auto-detect
setup_install_proxy() {
    echo -e "\n${MAGENTA}==================================================${NC}"
    print_lang "${MAGENTA}        НАСТРОЙКА УСТАНОВОЧНОГО ПРОКСИ (PIP)${NC}" "${MAGENTA}        INSTALLATION PROXY CONFIGURATION (PIP)${NC}"
    echo -e "${MAGENTA}==================================================${NC}"
    print_lang "Проверка прямого доступа к серверам Python (pypi.org)..." "Checking direct access to Python servers (pypi.org)..."

    INSTALL_PROXY=""
    if python3 -c "import urllib.request; urllib.request.urlopen('https://pypi.org', timeout=3)" 2>/dev/null; then
        print_lang "${GREEN}✓ Прямой доступ к PyPI стабилен. Прокси не требуется.${NC}" "${GREEN}✓ Direct access to PyPI is stable. No proxy needed.${NC}"
    else
        print_lang "${YELLOW}⚠️ Прямой доступ к PyPI отсутствует или заблокирован.${NC}" "${YELLOW}⚠️ Direct access to PyPI is missing or blocked.${NC}"
        
        # Try to auto-detect proxy from existing .env
        ENV_FILE="${SCRIPT_DIR}/config/.env"
        if [ -f "${ENV_FILE}" ]; then
            EXISTING_PROXY=$(grep -E "^PROXY_URL=" "${ENV_FILE}" | cut -d'=' -f2-)
            # Strip potential quotes or spaces
            EXISTING_PROXY=$(echo "${EXISTING_PROXY}" | tr -d '"' | tr -d "'")
            if [ -n "${EXISTING_PROXY}" ]; then
                print_lang "${GREEN}✓ Автоматически подтягиваем рабочий прокси из .env: ${YELLOW}${EXISTING_PROXY}${NC}" "${GREEN}✓ Auto-loading working proxy from .env: ${YELLOW}${EXISTING_PROXY}${NC}"
                INSTALL_PROXY="${EXISTING_PROXY}"
            fi
        fi

        if [ -z "${INSTALL_PROXY}" ]; then
            print_lang "${YELLOW}Хотите ли вы указать прокси-сервер вручную? (y/n) [n]${NC}" "${YELLOW}Do you want to specify a proxy server manually? (y/n) [n]${NC}"
            read -rp ">> " use_install_proxy
            if [ "${use_install_proxy}" = "y" ] || [ "${use_install_proxy}" = "Y" ]; then
                print_lang "\n${BLUE}Введите URL прокси (например, socks5://127.0.0.1:10808 или http://127.0.0.1:10809):${NC}" "\n${BLUE}Enter proxy URL (e.g. socks5://127.0.0.1:10808 or http://127.0.0.1:10809):${NC}"
                read -rp ">> " INSTALL_PROXY
                if [ -n "${INSTALL_PROXY}" ]; then
                    print_lang "${GREEN}✓ Установочный прокси настроен: ${INSTALL_PROXY}${NC}" "${GREEN}✓ Installation proxy configured: ${INSTALL_PROXY}${NC}"
                fi
            fi
        fi
    fi
}

# Функция для интерактивного опроса переменной
prompt_var() {
    local var_name=$1
    local prompt_text=$2
    local default_val=$3
    local current_val=""

    # Пытаемся извлечь текущее значение из существующего .env
    if [ -f "${ENV_FILE}" ]; then
        current_val=$(grep -E "^${var_name}=" "${ENV_FILE}" | cut -d'=' -f2-)
    fi

    # Если текущего значения нет, используем значение по умолчанию
    if [ -z "${current_val}" ]; then
        current_val="${default_val}"
    fi

    echo -e "\n${BLUE}👉 ${prompt_text}${NC}"
    if [ -n "${current_val}" ]; then
        print_lang "   ${CYAN}[Текущее значение / По умолчанию: ${YELLOW}${current_val}${CYAN}]${NC}" "   ${CYAN}[Current Value / Default: ${YELLOW}${current_val}${CYAN}]${NC}"
    fi
    if [ "${INSTALL_LANG}" = "ru" ]; then
        read -rp "   Введите значение (нажмите Enter для сохранения текущего): " user_input
    else
        read -rp "   Enter value (press Enter to keep current): " user_input
    fi

    if [ -z "${user_input}" ]; then
        user_input="${current_val}"
    fi

    local tmp_file="${ENV_FILE}.tmp"
    touch "${ENV_FILE}"
    > "$tmp_file"
    local found=0
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^${var_name}= ]]; then
            printf "%s\n" "${var_name}=${user_input}" >> "$tmp_file"
            found=1
        else
            printf "%s\n" "$line" >> "$tmp_file"
        fi
    done < "${ENV_FILE}"

    if [ $found -eq 0 ]; then
        printf "%s\n" "${var_name}=${user_input}" >> "$tmp_file"
    fi

    mv "$tmp_file" "${ENV_FILE}"
    print_lang "   ${GREEN}✓ Успешно сохранено: ${var_name}=${user_input}${NC}" "   ${GREEN}✓ Successfully saved: ${var_name}=${user_input}${NC}"
}

# Функция для интерактивного опроса булевой переменной (y/n)
prompt_bool() {
    local var_name=$1
    local prompt_text=$2
    local default_val=$3 # "True" или "False"
    local current_val=""

    # Пытаемся извлечь текущее значение из существующего .env
    if [ -f "${ENV_FILE}" ]; then
        current_val=$(grep -E "^${var_name}=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
    fi

    # Если текущего значения нет, используем значение по умолчанию
    if [ -z "${current_val}" ]; then
        current_val=$(echo "${default_val}" | tr '[:upper:]' '[:lower:]')
    fi

    # Переводим в формат y/n для отображения дефолта
    local default_yn="n"
    if [ "${current_val}" = "true" ] || [ "${current_val}" = "1" ] || [ "${current_val}" = "y" ] || [ "${current_val}" = "yes" ]; then
        default_yn="y"
    fi

    if [ "${INSTALL_LANG}" = "ru" ]; then
        echo -e "\n${BLUE}👉 ${prompt_text} (y/n) [по умолчанию: ${default_yn}]${NC}"
        read -rp "   Введите значение (y/n): " user_input
    else
        echo -e "\n${BLUE}👉 ${prompt_text} (y/n) [default: ${default_yn}]${NC}"
        read -rp "   Enter value (y/n): " user_input
    fi

    if [ -z "${user_input}" ]; then
        user_input="${default_yn}"
    fi

    user_input=$(echo "${user_input}" | tr '[:upper:]' '[:lower:]')

    local final_val="False"
    if [ "${user_input}" = "y" ] || [ "${user_input}" = "yes" ] || [ "${user_input}" = "true" ] || [ "${user_input}" = "1" ]; then
        final_val="True"
    fi

    # Для булевых значений sed полностью безопасен
    if grep -q "^${var_name}=" "${ENV_FILE}"; then
        sed -i "s/^${var_name}=.*/${var_name}=${final_val}/" "${ENV_FILE}"
    else
        echo "${var_name}=${final_val}" >> "${ENV_FILE}"
    fi
    print_lang "   ${GREEN}✓ Успешно сохранено: ${var_name}=${final_val}${NC}" "   ${GREEN}✓ Successfully saved: ${var_name}=${final_val}${NC}"
}
