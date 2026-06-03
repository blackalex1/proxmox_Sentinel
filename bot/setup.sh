#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Proxmox LXC Monitor Bot - Fully Automated Setup ===${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Ошибка: Этот скрипт должен быть запущен с правами ROOT (sudo).${NC}"
  echo -e "Пожалуйста, запустите его как: ${YELLOW}sudo ./setup.sh${NC}"
  exit 1
fi

# Get the absolute path of the directory containing the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo -e "Директория установки: ${GREEN}${SCRIPT_DIR}${NC}"

# Ask for installation proxy or auto-detect
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

# 1. Update apt and install python3-venv, python3-pip if missing
echo -e "\n${YELLOW}[1/5] Установка системных зависимостей (apt)...${NC}"
apt-get update
apt-get install -y python3-venv python3-pip python3-dev build-essential curl auditd

# 1.1 Настройка подсистемы аудита ядра (auditd)
echo -e "\n${YELLOW}[1.1/5] Настройка подсистемы аудита ядра (auditd)...${NC}"
if command -v auditctl >/dev/null 2>&1; then
    mkdir -p /etc/audit/rules.d
    AUDIT_RULES_FILE="/etc/audit/rules.d/audit.rules"
    RULE_STR="-a always,exit -F arch=b64 -S connect -k aegis_outbound"
    
    # Создаем файл, если его нет
    if [ ! -f "${AUDIT_RULES_FILE}" ]; then
        touch "${AUDIT_RULES_FILE}"
    fi

    if ! grep -Fq "${RULE_STR}" "${AUDIT_RULES_FILE}"; then
        echo "" >> "${AUDIT_RULES_FILE}"
        echo "${RULE_STR}" >> "${AUDIT_RULES_FILE}"
        echo -e "${GREEN}✓ Правило Aegis IPS добавлено в ${AUDIT_RULES_FILE}.${NC}"
    else
        echo -e "${GREEN}✓ Правило Aegis IPS уже присутствует в ${AUDIT_RULES_FILE}.${NC}"
    fi

    # Включаем и перезапускаем службу auditd
    systemctl enable auditd
    systemctl restart auditd
    echo -e "${GREEN}✓ Служба auditd успешно настроена и перезапущена.${NC}"
else
    echo -e "${RED}❌ Ошибка: Утилита auditctl не найдена после установки auditd.${NC}"
fi

# 2. Recreate venv
echo -e "\n${YELLOW}[2/5] Создание виртуального окружения (venv)...${NC}"
if [ -d "${SCRIPT_DIR}/venv" ]; then
    echo -e "Существующее окружение venv обнаружено. Пересоздаем..."
    rm -rf "${SCRIPT_DIR}/venv"
fi
python3 -m venv "${SCRIPT_DIR}/venv"
echo -e "${GREEN}✓ Виртуальное окружение venv создано.${NC}"

# 3. Upgrade pip and install requirements
echo -e "\n${YELLOW}[3/5] Обновление pip и установка библиотек...${NC}"

if [ -n "${INSTALL_PROXY}" ]; then
    # Check if SOCKS proxy is used
    if [[ "${INSTALL_PROXY}" == socks* ]]; then
        echo -e "${BLUE}Обнаружен SOCKS прокси. Начинаем бутстрап поддержки SOCKS для pip...${NC}"
        
        # Download PySocks wheel using curl with the proxy
        PYSOCKS_WHEEL="${SCRIPT_DIR}/venv/PySocks-1.7.1-py3-none-any.whl"
        echo -e "Скачивание библиотеки PySocks через прокси..."
        if curl -s -L --proxy "${INSTALL_PROXY}" -o "${PYSOCKS_WHEEL}" "https://files.pythonhosted.org/packages/41/ad/7eab6f1b4d34f111977d44fd2f6b866c1b370c48b2bf3276889a7f350064/PySocks-1.7.1-py3-none-any.whl"; then
            echo -e "${GREEN}✓ Библиотека PySocks успешно скачана.${NC}"
            # Install it locally
            "${SCRIPT_DIR}/venv/bin/pip" install "${PYSOCKS_WHEEL}"
            rm -f "${PYSOCKS_WHEEL}"
        else
            echo -e "${RED}❌ Не удалось скачать PySocks через прокси. Попробуем установить напрямую...${NC}"
        fi
    fi

    # Run pip with --proxy
    echo -e "Запуск pip с прокси: ${INSTALL_PROXY}"
    "${SCRIPT_DIR}/venv/bin/pip" install --proxy "${INSTALL_PROXY}" --upgrade pip
    "${SCRIPT_DIR}/venv/bin/pip" install --proxy "${INSTALL_PROXY}" -r "${SCRIPT_DIR}/requirements.txt"
else
    # Direct install
    "${SCRIPT_DIR}/venv/bin/pip" install --upgrade pip
    "${SCRIPT_DIR}/venv/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"
fi
echo -e "${GREEN}✓ Все зависимости установлены.${NC}"

# 4. Create and configure .env interactively
echo -e "\n${YELLOW}[4/5] Настройка файла .env...${NC}"
mkdir -p "${SCRIPT_DIR}/config"
ENV_FILE="${SCRIPT_DIR}/config/.env"
ENV_CREATED=0

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

ENV_EXISTS=0
if [ ! -f "${ENV_FILE}" ]; then
    if [ -f "${SCRIPT_DIR}/config/.env.example" ]; then
        cp "${SCRIPT_DIR}/config/.env.example" "${ENV_FILE}"
        echo -e "${YELLOW}⚠️ Создан файл .env из шаблона config/.env.example.${NC}"
        ENV_CREATED=1
    else
        echo -e "${RED}❌ Ошибка: Шаблон config/.env.example не найден. Создаем новый файл .env...${NC}"
        touch "${ENV_FILE}"
    fi
else
    echo -e "${GREEN}✓ Файл конфигурации .env уже существует. Интерактивная настройка пропущена.${NC}"
    ENV_EXISTS=1
fi

if [ ${ENV_EXISTS} -eq 0 ]; then
    echo -e "\n${MAGENTA}==================================================${NC}"
    echo -e "${MAGENTA}   ИНТЕРАКТИВНЫЙ МАСТЕР НАСТРОЙКИ КОНФИГУРАЦИИ .env${NC}"
    echo -e "${MAGENTA}==================================================${NC}"
    echo -e "Вы можете настроить бота прямо сейчас. Если вы нажмете Enter,"
    echo -e "будет сохранено текущее или дефолтное значение."
    
    echo -e "\n${YELLOW}Хотите ли вы настроить параметры .env интерактивно? (y/n) [y]${NC}"
    read -p ">> " run_wizard
    if [ -z "${run_wizard}" ] || [ "${run_wizard}" = "y" ] || [ "${run_wizard}" = "Y" ]; then
        # Запускаем интерактивный мастер
        prompt_var "BOT_TOKEN" "Токен вашего Telegram-бота (BOT_TOKEN)" ""
        prompt_var "ADMIN_IDS" "Telegram ID администраторов через запятую (ADMIN_IDS)" ""
        prompt_var "PROXMOX_HOST" "IP и порт вашего хоста Proxmox VE (PROXMOX_HOST)" "your_proxmox_ip:8006"
        prompt_var "PROXMOX_USER" "Имя пользователя Proxmox (PROXMOX_USER)" "root@pam"
        prompt_var "PROXMOX_TOKEN_ID" "Proxmox API Token ID (PROXMOX_TOKEN_ID)" ""
        prompt_var "PROXMOX_TOKEN_SECRET" "Proxmox API Token Secret (PROXMOX_TOKEN_SECRET)" ""
        
        # Мониторинг VPS
        prompt_var "REMOTE_MONITOR_ENABLE" "Включить мониторинг удаленного сервера VPS? (True/False)" "False"
        local vps_enabled=$(grep -E "^REMOTE_MONITOR_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
        if [ "${vps_enabled}" = "true" ] || [ "${vps_enabled}" = "1" ] || [ "${vps_enabled}" = "y" ] || [ "${vps_enabled}" = "yes" ]; then
            prompt_var "REMOTE_SERVER_IP" "IP-адрес удаленного сервера VPS (REMOTE_SERVER_IP)" ""
            prompt_var "REMOTE_SERVER_USER" "Имя пользователя SSH на VPS (REMOTE_SERVER_USER)" "root"
            prompt_var "REMOTE_SERVER_SSH_KEY" "Имя ключа или путь к приватному SSH ключу (REMOTE_SERVER_SSH_KEY)" "id_rsa_remote"
            prompt_var "REMOTE_MONITOR_IGNORE_KEYS" "Игнорировать успешные входы по SSH с данных ключей (через запятую)" "bot@bot"
            prompt_var "REMOTE_MONITOR_IGNORE_IPS" "Игнорировать успешные входы по SSH с данных IP-адресов (через запятую)" ""
        fi
    
        # Настройки 3X-UI
        prompt_var "XUI_HOST" "URL-адрес панели 3X-UI (XUI_HOST, например: https://your_xui_ip:port/path/)" ""
        prompt_var "XUI_USERNAME" "Имя пользователя 3X-UI (XUI_USERNAME)" ""
        prompt_var "XUI_PASSWORD" "Пароль 3X-UI (XUI_PASSWORD)" ""
        
        # Настройки прокси для Telegram
        prompt_var "PROXY_URL" "Прокси для Telegram (PROXY_URL, оставьте пустым если не требуется)" "${INSTALL_PROXY}"
    
        # Мониторинг роутера Mihomo (Clash.Meta) и автоматический бан
        prompt_var "MIHOMO_MONITOR_ENABLE" "Включить мониторинг роутера через Mihomo API? (True/False)" "False"
        local mihomo_enabled=$(grep -E "^MIHOMO_MONITOR_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
        if [ "${mihomo_enabled}" = "true" ] || [ "${mihomo_enabled}" = "1" ] || [ "${mihomo_enabled}" = "y" ] || [ "${mihomo_enabled}" = "yes" ]; then
            prompt_var "MIHOMO_API_HOST" "IP-адрес REST API роутера Mihomo (MIHOMO_API_HOST)" "192.168.1.1"
            prompt_var "MIHOMO_API_PORT" "Порт REST API роутера Mihomo (MIHOMO_API_PORT)" "9090"
            prompt_var "MIHOMO_API_SECRET" "Секретный токен API Mihomo (MIHOMO_API_SECRET, оставьте пустым если нет)" ""
            prompt_var "MIHOMO_AUTO_BAN" "Включить автоматический бан нарушителей на роутере? (True/False)" "False"
            prompt_var "MIHOMO_MAX_VIOLATIONS" "Лимит попыток доступа до автоблокировки (MIHOMO_MAX_VIOLATIONS)" "3"
            
            prompt_var "ROUTER_SSH_ENABLE" "Разрешить боту подключаться к роутеру по SSH для блокировок? (True/False)" "False"
            local r_ssh_enabled=$(grep -E "^ROUTER_SSH_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
            if [ "${r_ssh_enabled}" = "true" ] || [ "${r_ssh_enabled}" = "1" ] || [ "${r_ssh_enabled}" = "y" ] || [ "${r_ssh_enabled}" = "yes" ]; then
                prompt_var "ROUTER_SSH_HOST" "IP-адрес SSH роутера (ROUTER_SSH_HOST)" "192.168.1.1"
                prompt_var "ROUTER_SSH_PORT" "Порт SSH роутера (ROUTER_SSH_PORT)" "22"
                prompt_var "ROUTER_SSH_USER" "Имя пользователя SSH роутера (ROUTER_SSH_USER)" "root"
                prompt_var "ROUTER_SSH_PASSWORD" "Пароль SSH роутера (ROUTER_SSH_PASSWORD, если пустой - будет использоваться ключ)" ""
                prompt_var "ROUTER_SSH_KEY" "Путь к приватному SSH ключу роутера (ROUTER_SSH_KEY)" "config/id_rsa_router"
                prompt_var "ROUTER_TYPE" "Тип операционной системы роутера (openwrt/keenetic/generic)" "openwrt"
            fi
        fi
    
        ENV_CREATED=0 # Сбрасываем предупреждение, так как переменные заполнены!
        echo -e "\n${GREEN}🎉 Конфигурация .env успешно завершена!${NC}"
    else
        echo -e "\n${YELLOW}⚠️ Интерактивная настройка пропущена. Отредактируйте .env вручную.${NC}"
    fi
fi

# 5. Create and install systemd service dynamically with current paths
echo -e "\n${YELLOW}[5/5] Создание и установка службы systemd...${NC}"
SERVICE_PATH="/etc/systemd/system/proxmox-lxc-bot.service"

cat <<EOF > "${SERVICE_PATH}"
[Unit]
Description=Proxmox LXC Monitor Telegram Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${SCRIPT_DIR}/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=proxmox-lxc-bot

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Файл службы создан: ${SERVICE_PATH}${NC}"

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable proxmox-lxc-bot.service

if [ ${ENV_CREATED} -eq 1 ]; then
    echo -e "\n${YELLOW}==================================================${NC}"
    echo -e "${YELLOW}🎉 Настройка завершена с предупреждением!${NC}"
    echo -e "=================================================="
    echo -e "Служба добавлена в автозапуск, но НЕ запущена, так как файл .env пустой."
    echo -e "👉 ${BLUE}Отредактируйте .env: ${YELLOW}nano ${ENV_FILE}${NC}"
    echo -e "👉 ${BLUE}Запустите службу: ${YELLOW}systemctl start proxmox-lxc-bot.service${NC}"
    echo -e "=================================================="
else
    # Start the service
    echo -e "Запуск фоновой службы бота..."
    systemctl restart proxmox-lxc-bot.service
    echo -e "\n${GREEN}==================================================${NC}"
    echo -e "${GREEN}🎉 Настройка и запуск успешно завершены!${NC}"
    echo -e "=================================================="
    echo -e "Служба: ${BLUE}proxmox-lxc-bot.service${NC} активна и в автозапуске."
    echo -e "Смотреть логи: ${YELLOW}journalctl -u proxmox-lxc-bot -f${NC}"
    echo -e "=================================================="
fi
