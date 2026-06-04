#!/usr/bin/env bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Ошибка: Этот скрипт должен быть запущен с правами ROOT (sudo).${NC}"
        echo -e "Пожалуйста, запустите его как: ${YELLOW}sudo ./setup.sh${NC}"
        exit 1
    fi
}

# Display welcome banner
show_welcome_banner() {
    echo -e "${BLUE}=== Proxmox LXC Monitor Bot - Fully Automated Setup ===${NC}"
    echo -e "Директория установки: ${GREEN}${SCRIPT_DIR}${NC}"
}

# Ask for installation proxy or auto-detect
setup_install_proxy() {
    echo -e "\n${MAGENTA}==================================================${NC}"
    echo -e "${MAGENTA}        НАСТРОЙКА УСТАНОВОЧНОГО ПРОКСИ (PIP)${NC}"
    echo -e "${MAGENTA}==================================================${NC}"
    echo -e "Проверка прямого доступа к серверам Python (pypi.org)..."

    INSTALL_PROXY=""
    if python3 -c "import urllib.request; urllib.request.urlopen('https://pypi.org', timeout=3)" 2>/dev/null; then
        echo -e "${GREEN}✓ Прямой доступ к PyPI стабилен. Прокси не требуется.${NC}"
    else
        echo -e "${YELLOW}⚠️ Прямой доступ к PyPI отсутствует или заблокирован.${NC}"
        
        # Try to auto-detect proxy from existing .env
        ENV_FILE="${SCRIPT_DIR}/config/.env"
        if [ -f "${ENV_FILE}" ]; then
            EXISTING_PROXY=$(grep -E "^PROXY_URL=" "${ENV_FILE}" | cut -d'=' -f2-)
            # Strip potential quotes or spaces
            EXISTING_PROXY=$(echo "${EXISTING_PROXY}" | tr -d '"' | tr -d "'")
            if [ -n "${EXISTING_PROXY}" ]; then
                echo -e "${GREEN}✓ Автоматически подтягиваем рабочий прокси из .env: ${YELLOW}${EXISTING_PROXY}${NC}"
                INSTALL_PROXY="${EXISTING_PROXY}"
            fi
        fi

        if [ -z "${INSTALL_PROXY}" ]; then
            echo -e "${YELLOW}Хотите ли вы указать прокси-сервер вручную? (y/n) [n]${NC}"
            read -p ">> " use_install_proxy
            if [ "${use_install_proxy}" = "y" ] || [ "${use_install_proxy}" = "Y" ]; then
                echo -e "\n${BLUE}Введите URL прокси (например, socks5://127.0.0.1:10808 или http://127.0.0.1:10809):${NC}"
                read -p ">> " INSTALL_PROXY
                if [ -n "${INSTALL_PROXY}" ]; then
                    echo -e "${GREEN}✓ Установочный прокси настроен: ${INSTALL_PROXY}${NC}"
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
        echo -e "   ${CYAN}[Текущее значение / По умолчанию: ${YELLOW}${current_val}${CYAN}]${NC}"
    fi
    read -p "   Введите значение (нажмите Enter для сохранения текущего): " user_input

    if [ -z "${user_input}" ]; then
        user_input="${current_val}"
    fi

    # Экранируем слеши и спецсимволы для корректной замены в sed
    local escaped_input=$(echo "${user_input}" | sed 's/\//\\\//g' | sed 's/\&/\\\&/g')

    if grep -q "^${var_name}=" "${ENV_FILE}"; then
        sed -i "s/^${var_name}=.*/${var_name}=${escaped_input}/" "${ENV_FILE}"
    else
        echo "${var_name}=${user_input}" >> "${ENV_FILE}"
    fi
    echo -e "   ${GREEN}✓ Успешно сохранено: ${var_name}=${user_input}${NC}"
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

    echo -e "\n${BLUE}👉 ${prompt_text} (y/n) [по умолчанию: ${default_yn}]${NC}"
    read -p "   Введите значение (y/n): " user_input

    if [ -z "${user_input}" ]; then
        user_input="${default_yn}"
    fi

    user_input=$(echo "${user_input}" | tr '[:upper:]' '[:lower:]')

    local final_val="False"
    if [ "${user_input}" = "y" ] || [ "${user_input}" = "yes" ] || [ "${user_input}" = "true" ] || [ "${user_input}" = "1" ]; then
        final_val="True"
    fi

    # Экранируем и сохраняем
    if grep -q "^${var_name}=" "${ENV_FILE}"; then
        sed -i "s/^${var_name}=.*/${var_name}=${final_val}/" "${ENV_FILE}"
    else
        echo "${var_name}=${final_val}" >> "${ENV_FILE}"
    fi
    echo -e "   ${GREEN}✓ Успешно сохранено: ${var_name}=${final_val}${NC}"
}
