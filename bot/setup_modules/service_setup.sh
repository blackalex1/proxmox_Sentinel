#!/usr/bin/env bash

# Create and install systemd service dynamically with current paths
install_systemd_service() {
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
}

# Scan and check firewall settings on PVE containers
check_lxc_firewalls() {
    if [ -d "/etc/pve/lxc" ]; then
        echo -e "\n${CYAN}🔎 Проверка настроек Firewall в контейнерах LXC...${NC}"
        declare -a missing_fw_containers
        
        shopt -s nullglob
        for conf_file in /etc/pve/lxc/*.conf; do
            if [ -f "$conf_file" ]; then
                vmid=$(basename "$conf_file" .conf)
                net_interfaces=$(grep -E "^net[0-9]+:" "$conf_file" || true)
                if [ -n "$net_interfaces" ]; then
                    has_interfaces=0
                    fw_enabled=1
                    while read -r net_line; do
                        if [ -n "$net_line" ]; then
                            has_interfaces=1
                            if [[ ! "$net_line" =~ "firewall=1" ]]; then
                                fw_enabled=0
                            fi
                        fi
                    done <<< "$net_interfaces"
                    
                    if [ $has_interfaces -eq 1 ] && [ $fw_enabled -eq 0 ]; then
                        missing_fw_containers+=("$vmid")
                    fi
                fi
            fi
        done
        shopt -u nullglob
        
        if [ ${#missing_fw_containers[@]} -gt 0 ]; then
            echo -e "${YELLOW}⚠️ ВНИМАНИЕ: Фаервол отключен для некоторых контейнеров LXC!${NC}"
            echo -e "${YELLOW}В настройках сетевых интерфейсов следующих контейнеров не включена опция 'Firewall':${NC}"
            for vmid in "${missing_fw_containers[@]}"; do
                echo -e "   - Контейнер ID: ${YELLOW}${vmid}${NC}"
            done
            echo -e "${YELLOW}Для корректной фильтрации трафика рекомендуется включить Firewall в опциях сетевых карт этих LXC.${NC}"
        else
            echo -e "${GREEN}✓ Все контейнеры LXC имеют включенный Firewall на сетевых интерфейсах.${NC}"
        fi
    fi
}

# Restart service and verify start logs
start_service_and_verify() {
    if [ ${ENV_CREATED} -eq 1 ]; then
        echo -e "\n${YELLOW}==================================================${NC}"
        echo -e "${YELLOW}🎉 Настройка завершена с предупреждением!${NC}"
        echo -e "=================================================="
        echo -e "Служба добавлена в автозапуск, но НЕ запущена, так как файл .env пустой."
        echo -e "👉 ${BLUE}Отредактируйте .env: ${YELLOW}nano ${ENV_FILE}${NC}"
        echo -e "👉 ${BLUE}Запустите службу: ${YELLOW}systemctl start proxmox-lxc-bot.service${NC}"
        echo -e "=================================================="
        
        check_lxc_firewalls
    else
        # Start the service
        echo -e "Запуск фоновой службы бота..."
        systemctl restart proxmox-lxc-bot.service
        
        echo -e "Ожидание инициализации службы (3 секунды)..."
        sleep 3
        
        echo -e "\n${BLUE}=== Последние логи запуска службы proxmox-lxc-bot ===${NC}"
        journalctl -u proxmox-lxc-bot.service -n 12 --no-pager || true
        echo -e "${BLUE}=====================================================${NC}"
        
        check_lxc_firewalls

        echo -e "\n${GREEN}==================================================${NC}"
        echo -e "${GREEN}🎉 Настройка и запуск успешно завершены!${NC}"
        echo -e "=================================================="
        echo -e "Служба: ${BLUE}proxmox-lxc-bot.service${NC} активна и в автозапуске."
        echo -e "Смотреть логи: ${YELLOW}journalctl -u proxmox-lxc-bot -f${NC}"
        echo -e "=================================================="
        
        echo -e "\n${YELLOW}Хотите ли вы запустить автоматические E2E тесты IPS прямо сейчас? (y/n) [y]${NC}"
        read -p ">> " run_tests
        if [ -z "${run_tests}" ] || [ "${run_tests}" = "y" ] || [ "${run_tests}" = "Y" ]; then
            echo -e "\n${BLUE}Запуск E2E тестов IPS...${NC}"
            "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/setup_modules/test_ips.py"
        fi
    fi
}
