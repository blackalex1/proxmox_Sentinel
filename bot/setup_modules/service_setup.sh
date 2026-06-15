#!/usr/bin/env bash

# Create and install systemd service dynamically with current paths
install_systemd_service() {
    print_lang "\n${YELLOW}[5/5] Создание и установка службы systemd...${NC}" "\n${YELLOW}[5/5] Creating and installing systemd service...${NC}"
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

    print_lang "${GREEN}✓ Файл службы создан: ${SERVICE_PATH}${NC}" "${GREEN}✓ Service file created: ${SERVICE_PATH}${NC}"

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable proxmox-lxc-bot.service
}

# Scan and check firewall settings on PVE containers
check_lxc_firewalls() {
    if [ -d "/etc/pve/lxc" ]; then
        print_lang "\n${CYAN}🔎 Проверка настроек Firewall в контейнерах LXC...${NC}" "\n${CYAN}🔎 Checking Firewall settings in LXC containers...${NC}"
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
            print_lang "${YELLOW}⚠️ ВНИМАНИЕ: Фаервол отключен для некоторых контейнеров LXC!${NC}" "${YELLOW}⚠️ WARNING: Firewall is disabled for some LXC containers!${NC}"
            print_lang "${YELLOW}В настройках сетевых интерфейсов следующих контейнеров не включена опция 'Firewall':${NC}" "${YELLOW}The following containers do not have 'Firewall' enabled in their network interface options:${NC}"
            for vmid in "${missing_fw_containers[@]}"; do
                print_lang "   - Контейнер ID: ${YELLOW}${vmid}${NC}" "   - Container ID: ${YELLOW}${vmid}${NC}"
            done
            print_lang "${YELLOW}Для корректной фильтрации трафика рекомендуется включить Firewall в опциях сетевых карт этих LXC.${NC}" "${YELLOW}It is recommended to enable Firewall in the network card options of these LXCs for correct traffic filtering.${NC}"
        else
            print_lang "${GREEN}✓ Все контейнеры LXC имеют включенный Firewall на сетевых интерфейсах.${NC}" "${GREEN}✓ All LXC containers have Firewall enabled on network interfaces.${NC}"
        fi
    fi
}

# Restart service and verify start logs
start_service_and_verify() {
    if [ ${ENV_CREATED} -eq 1 ]; then
        echo -e "\n${YELLOW}==================================================${NC}"
        print_lang "${YELLOW}🎉 Настройка завершена с предупреждением!${NC}" "${YELLOW}🎉 Setup completed with warnings!${NC}"
        echo -e "=================================================="
        print_lang "Служба добавлена в автозапуск, но НЕ запущена, так как файл .env пустой." "Service added to autostart but NOT started because .env file is empty."
        print_lang "👉 ${BLUE}Отредактируйте .env: ${YELLOW}nano ${ENV_FILE}${NC}" "👉 ${BLUE}Edit .env: ${YELLOW}nano ${ENV_FILE}${NC}"
        print_lang "👉 ${BLUE}Запустите службу: ${YELLOW}systemctl start proxmox-lxc-bot.service${NC}" "👉 ${BLUE}Start service: ${YELLOW}systemctl start proxmox-lxc-bot.service${NC}"
        echo -e "=================================================="
        
        check_lxc_firewalls
    else
        # Start the service
        print_lang "Запуск фоновой службы бота..." "Starting background bot service..."
        systemctl restart proxmox-lxc-bot.service
        
        print_lang "Ожидание инициализации службы (3 секунды)..." "Waiting for service initialization (3 seconds)..."
        sleep 3
        
        print_lang "\n${BLUE}=== Последние логи запуска службы proxmox-lxc-bot ===${NC}" "\n${BLUE}=== Latest start logs of proxmox-lxc-bot service ===${NC}"
        journalctl -u proxmox-lxc-bot.service -n 12 --no-pager || true
        echo -e "${BLUE}=====================================================${NC}"
        
        check_lxc_firewalls

        echo -e "\n${GREEN}==================================================${NC}"
        print_lang "${GREEN}🎉 Настройка и запуск успешно завершены!${NC}" "${GREEN}🎉 Setup and start completed successfully!${NC}"
        echo -e "=================================================="
        print_lang "Служба: ${BLUE}proxmox-lxc-bot.service${NC} активна и в автозапуске." "Service: ${BLUE}proxmox-lxc-bot.service${NC} is active and enabled."
        print_lang "Смотреть логи: ${YELLOW}journalctl -u proxmox-lxc-bot -f${NC}" "View logs: ${YELLOW}journalctl -u proxmox-lxc-bot -f${NC}"
        echo -e "=================================================="
        
        print_lang "\n${YELLOW}Хотите ли вы запустить автоматические E2E тесты IPS прямо сейчас? (y/n) [y]${NC}" "\n${YELLOW}Do you want to run automatic E2E IPS tests now? (y/n) [y]${NC}"
        read -rp ">> " run_tests
        if [ -z "${run_tests}" ] || [ "${run_tests}" = "y" ] || [ "${run_tests}" = "Y" ]; then
            print_lang "\n${BLUE}Запуск E2E тестов IPS...${NC}" "\n${BLUE}Running E2E IPS tests...${NC}"
            "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/setup_modules/test_ips.py"
        fi
    fi
}
