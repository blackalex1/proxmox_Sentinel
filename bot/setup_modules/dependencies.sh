#!/usr/bin/env bash

# Install system dependencies (apt)
install_system_deps() {
    echo -e "\n${YELLOW}[1/5] Установка системных зависимостей (apt)...${NC}"
    apt-get update
    apt-get install -y python3-venv python3-pip python3-dev build-essential curl auditd
}

# Configure auditd कनेक्ट rules
configure_auditd() {
    echo -e "\n${YELLOW}[1.1/5] Настройка подсистемы аудита ядра (auditd)...${NC}"
    if command -v auditctl >/dev/null 2>&1; then
        mkdir -p /etc/audit/rules.d
        AUDIT_RULES_FILE="/etc/audit/rules.d/audit.rules"
        RULE_STR="-a always,exit -F arch=b64 -S connect -k aegis_outbound"
        
        # Создаем файл, если его нет
        if [ ! -f "${AUDIT_RULES_FILE}" ]; then
            touch "${AUDIT_RULES_FILE}"
        fi

        if ! grep -Fq -- "${RULE_STR}" "${AUDIT_RULES_FILE}"; then
            echo "" >> "${AUDIT_RULES_FILE}"
            echo "${RULE_STR}" >> "${AUDIT_RULES_FILE}"
            echo -e "${GREEN}✓ Правило Aegis IPS добавлено в ${AUDIT_RULES_FILE}.${NC}"
        else
            echo -e "${GREEN}✓ Правило Aegis IPS уже присутствует в ${AUDIT_RULES_FILE}.${NC}"
        fi

        # Включаем и перезапускаем службу auditd (игнорируя ошибки, если ядро не поддерживает аудит)
        systemctl enable auditd || true
        systemctl restart auditd || echo -e "${YELLOW}⚠️ Предупреждение: Не удалось запустить auditd. Это нормально, если в GRUB отключен аудит (audit=0).${NC}"
        echo -e "${GREEN}✓ Служба auditd настроена.${NC}"
    else
        echo -e "${RED}❌ Ошибка: Утилита auditctl не найдена после установки auditd.${NC}"
    fi
}

# Setup Python Venv and requirements
setup_python_venv() {
    echo -e "\n${YELLOW}[2/5] Создание виртуального окружения (uv venv)...${NC}"

    # Install uv if missing
    if ! command -v uv >/dev/null 2>&1; then
        echo -e "Установка fast-installer (uv)..."
        curl -LsSf https://astral.sh/uv/install.sh | INSTALLER_NO_MODIFY_PATH=1 sh || pip3 install uv --break-system-packages || pip install uv
        export PATH="${HOME}/.local/bin:${PATH}"
    fi

    # Use uv path helper
    UV_BIN="uv"
    if [ -f "${HOME}/.local/bin/uv" ]; then
        UV_BIN="${HOME}/.local/bin/uv"
    elif [ -f "/root/.local/bin/uv" ]; then
        UV_BIN="/root/.local/bin/uv"
    fi

    if [ -d "${SCRIPT_DIR}/venv" ]; then
        echo -e "Существующее окружение venv обнаружено. Пересоздаем..."
        rm -rf "${SCRIPT_DIR}/venv"
    fi

    $UV_BIN venv "${SCRIPT_DIR}/venv"
    echo -e "${GREEN}✓ Виртуальное окружение venv создано с помощью uv.${NC}"
}

install_python_requirements() {
    echo -e "\n${YELLOW}[3/5] Установка библиотек через uv...${NC}"

    if [ -n "${INSTALL_PROXY}" ]; then
        echo -e "Запуск uv с прокси: ${INSTALL_PROXY}"
        export HTTP_PROXY="${INSTALL_PROXY}"
        export HTTPS_PROXY="${INSTALL_PROXY}"
        export ALL_PROXY="${INSTALL_PROXY}"
    fi

    # Use uv path helper again
    UV_BIN="uv"
    if [ -f "${HOME}/.local/bin/uv" ]; then
        UV_BIN="${HOME}/.local/bin/uv"
    elif [ -f "/root/.local/bin/uv" ]; then
        UV_BIN="/root/.local/bin/uv"
    fi

    $UV_BIN pip install --python "${SCRIPT_DIR}/venv" -r "${SCRIPT_DIR}/requirements.txt"
    echo -e "${GREEN}✓ Все зависимости установлены с помощью uv.${NC}"
}
