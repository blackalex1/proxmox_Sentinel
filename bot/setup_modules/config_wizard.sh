#!/usr/bin/env bash

# Run interactive environment configuration wizard
run_config_wizard() {
    echo -e "\n${YELLOW}[4/5] Настройка файла .env...${NC}"
    mkdir -p "${SCRIPT_DIR}/config"
    ENV_FILE="${SCRIPT_DIR}/config/.env"
    ENV_CREATED=0

    ENV_EXISTS=0
    ENV_WAS_PRESENT=0
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
        echo -e "${GREEN}✓ Файл конфигурации .env уже существует.${NC}"
        echo -e "Хотите перезапустить интерактивный мастер настройки и обновить .env? (y/n) [n]"
        read -rp ">> " rerun_wizard
        if [ "${rerun_wizard}" = "y" ] || [ "${rerun_wizard}" = "Y" ]; then
            ENV_EXISTS=0
            ENV_WAS_PRESENT=1
        else
            ENV_EXISTS=1
        fi
    fi

    if [ ${ENV_EXISTS} -eq 0 ]; then
        echo -e "\n${MAGENTA}==================================================${NC}"
        echo -e "${MAGENTA}   ИНТЕРАКТИВНЫЙ МАСТЕР НАСТРОЙКИ КОНФИГУРАЦИИ .env${NC}"
        echo -e "${MAGENTA}==================================================${NC}"
        echo -e "Вы можете настроить бота прямо сейчас. Если вы нажмете Enter,"
        echo -e "будет сохранено текущее или дефолтное значение."

        # 1. Автоопределение IP хоста Proxmox VE
        DETECTED_IP=""
        if command -v ip >/dev/null 2>&1; then
            DETECTED_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' || true)
        fi
        if [ -z "${DETECTED_IP}" ]; then
            DETECTED_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
        fi
        if [ -z "${DETECTED_IP}" ]; then
            DETECTED_IP="127.0.0.1"
        fi
        PVE_HOST_DEFAULT="${DETECTED_IP}:8006"

        # 2. Автоопределение SSH IP администратора
        DETECTED_SSH_IP=""
        if [ -n "${SSH_CLIENT}" ]; then
            DETECTED_SSH_IP=$(echo "${SSH_CLIENT}" | awk '{print $1}')
        elif [ -n "${SSH_CONNECTION}" ]; then
            DETECTED_SSH_IP=$(echo "${SSH_CONNECTION}" | awk '{print $1}')
        fi
        
        TRUSTED_IPS_DEFAULT="your_admin_ip"
        if [ -n "${DETECTED_SSH_IP}" ]; then
            echo -e "\n${CYAN}Обнаружен ваш IP-адрес подключения по SSH: ${YELLOW}${DETECTED_SSH_IP}${NC}"
            echo -e "Добавить его в белый список доверенных IP (TRUSTED_ADMIN_IPS)? (y/n) [y]"
            read -rp ">> " add_ssh_ip
            if [ -z "${add_ssh_ip}" ] || [ "${add_ssh_ip}" = "y" ] || [ "${add_ssh_ip}" = "Y" ]; then
                TRUSTED_IPS_DEFAULT="${DETECTED_SSH_IP}"
            fi
        fi

        # 3. Автогенерация или использование существующего API-токена Proxmox через pveum
        AUTO_TOKEN_ID=""
        AUTO_TOKEN_SECRET=""
        if command -v pveum >/dev/null 2>&1; then
            echo -e "\n${GREEN}✓ Обнаружен Proxmox VE (утилита pveum доступна).${NC}"
            
            # Получаем список существующих токенов для root@pam
            TOKENS_JSON=$(pveum user token list root@pam --output-format json 2>/dev/null || echo "[]")
            # Парсим имена токенов через Python
            EXISTING_TOKENS=$(python3 -c "import sys, json; tokens = json.loads(sys.stdin.read()); print(','.join([t.get('tokenid', '') for t in tokens if 'tokenid' in t]))" <<< "${TOKENS_JSON}" 2>/dev/null || true)
            
            token_choice="new"
            if [ -n "${EXISTING_TOKENS}" ]; then
                echo -e "${CYAN}Обнаружены существующие API-токены Proxmox для пользователя root@pam:${NC}"
                IFS=',' read -r -a token_array <<< "${EXISTING_TOKENS}"
                for i in "${!token_array[@]}"; do
                    echo -e "  $((i+1))) root@pam!${token_array[i]}"
                done
                echo -e "  $(( ${#token_array[@]} + 1 ))) [Создать новый API-токен]"
                
                echo -e "\n${YELLOW}Выберите номер токена для использования (или создайте новый):${NC}"
                read -rp ">> " user_token_selection
                
                # Проверяем корректность выбора
                if [[ "$user_token_selection" =~ ^[0-9]+$ ]] && [ "$user_token_selection" -ge 1 ] && [ "$user_token_selection" -le "${#token_array[@]}" ]; then
                    selected_token_name="${token_array[$((user_token_selection-1))]}"
                    AUTO_TOKEN_ID="root@pam!${selected_token_name}"
                    echo -e "${GREEN}✓ Выбран существующий токен: ${AUTO_TOKEN_ID}${NC}"
                    echo -e "${BLUE}👉 Введите секретный код (Secret Value) для этого токена:${NC}"
                    read -rp ">> " AUTO_TOKEN_SECRET
                    token_choice="existing"
                else
                    token_choice="new"
                fi
            fi
            
            if [ "${token_choice}" = "new" ]; then
                echo -e "\nХотите ли вы автоматически сгенерировать новый выделенный API-токен для работы бота? (y/n) [y]"
                read -rp ">> " generate_token_pve
                if [ -z "${generate_token_pve}" ] || [ "${generate_token_pve}" = "y" ] || [ "${generate_token_pve}" = "Y" ]; then
                    echo -e "Введите имя нового токена [по умолчанию: aegis-ips]:"
                    read -rp ">> " new_token_name
                    if [ -z "${new_token_name}" ]; then
                        new_token_name="aegis-ips"
                    fi
                    
                    echo -e "Генерация API-токена 'root@pam!${new_token_name}'..."
                    # Удаляем старый токен с таким же именем, если он был
                    pveum user token delete root@pam "${new_token_name}" 2>/dev/null || true
                    # Создаем новый токен
                    TOKEN_OUT=$(pveum user token add root@pam "${new_token_name}" --privsep 0 --output-format json 2>/dev/null || true)
                    if [ -n "${TOKEN_OUT}" ]; then
                        TOKEN_SECRET=$(python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('value', ''))" <<< "${TOKEN_OUT}" 2>/dev/null || true)
                        if [ -n "${TOKEN_SECRET}" ]; then
                            echo -e "${GREEN}✓ API-токен успешно сгенерирован!${NC}"
                            AUTO_TOKEN_ID="root@pam!${new_token_name}"
                            AUTO_TOKEN_SECRET="${TOKEN_SECRET}"
                        else
                            echo -e "${RED}⚠️ Не удалось извлечь секрет токена из вывода pveum.${NC}"
                        fi
                    else
                        echo -e "${RED}⚠️ Ошибка при создании токена через pveum.${NC}"
                    fi
                fi
            fi
        fi

        # 4. Автоопределение LXC контейнеров для VPN_VMID
        AUTO_VPN_VMID=""
        if command -v pct >/dev/null 2>&1; then
            echo -e "\n${CYAN}Поиск контейнеров LXC на хосте Proxmox VE...${NC}"
            LXC_LIST=$(pct list 2>/dev/null | tail -n +2 | awk '{print $1, $2, $NF}' || true)
            
            if [ -n "$LXC_LIST" ]; then
                declare -a vmid_array
                declare -a name_array
                declare -a status_array
                
                idx=0
                auto_idx=-1
                while read -r vmid status name; do
                    if [ -n "$vmid" ]; then
                        vmid_array[idx]=$vmid
                        name_array[idx]=$name
                        status_array[idx]=$status
                        
                        lower_name=$(echo "$name" | tr '[:upper:]' '[:lower:]')
                        if [[ "$lower_name" =~ vpn || "$lower_name" =~ wg || "$lower_name" =~ wireguard || "$lower_name" =~ openvpn || "$lower_name" =~ xray || "$lower_name" =~ 3x-ui || "$lower_name" =~ xui ]]; then
                            if [ $auto_idx -eq -1 ]; then
                                auto_idx=$idx
                            fi
                        fi
                        idx=$((idx+1))
                    fi
                done <<< "$LXC_LIST"
                
                if [ ${#vmid_array[@]} -gt 0 ]; then
                    echo -e "Найденные контейнеры LXC:"
                    for i in "${!vmid_array[@]}"; do
                        if [ $i -eq $auto_idx ]; then
                            echo -e "  $((i+1))) ${GREEN}${vmid_array[i]} - ${name_array[i]} (Статус: ${status_array[i]}) [Автоопределение: VPN]${NC}"
                        else
                            echo -e "  $((i+1))) ${vmid_array[i]} - ${name_array[i]} (Статус: ${status_array[i]})"
                        fi
                    done
                    echo -e "  $(( ${#vmid_array[@]} + 1 ))) [Ввести ID вручную]"
                    
                    default_option=""
                    if [ $auto_idx -ne -1 ]; then
                        default_option=$((auto_idx+1))
                    fi
                    
                    echo -e "\n${YELLOW}Выберите порядковый номер из списка (1, 2...) или введите ID контейнера (например, 101) для VPN_VMID [по умолчанию: ${default_option:-ID вручную}]:${NC}"
                    read -rp ">> " user_lxc_selection
                    
                    if [ -z "$user_lxc_selection" ] && [ -n "$default_option" ]; then
                        user_lxc_selection=$default_option
                    fi
                    
                    if [[ "$user_lxc_selection" =~ ^[0-9]+$ ]]; then
                        # Сначала проверяем, не введен ли порядковый номер из списка
                        if [ "$user_lxc_selection" -ge 1 ] && [ "$user_lxc_selection" -le "${#vmid_array[@]}" ]; then
                            AUTO_VPN_VMID="${vmid_array[$((user_lxc_selection-1))]}"
                            echo -e "${GREEN}✓ Выбран контейнер: ${AUTO_VPN_VMID} (${name_array[$((user_lxc_selection-1))]})${NC}"
                        else
                            # Иначе проверяем, не введен ли реальный VMID напрямую
                            for i in "${!vmid_array[@]}"; do
                                if [ "${vmid_array[i]}" -eq "$user_lxc_selection" ]; then
                                    AUTO_VPN_VMID="$user_lxc_selection"
                                    echo -e "${GREEN}✓ Выбран контейнер по прямому ID: ${AUTO_VPN_VMID} (${name_array[i]})${NC}"
                                    break
                                fi
                            done
                        fi
                    fi
                fi
            fi
        fi
        
        local run_wizard="y"
        if [ ${ENV_WAS_PRESENT} -eq 0 ]; then
            echo -e "\n${YELLOW}Хотите ли вы настроить параметры .env интерактивно? (y/n) [y]${NC}"
            read -rp ">> " run_wizard
        fi
        if [ -z "${run_wizard}" ] || [ "${run_wizard}" = "y" ] || [ "${run_wizard}" = "Y" ]; then
            # Запускаем интерактивный мастер
            prompt_var "BOT_TOKEN" "Токен вашего Telegram-бота (BOT_TOKEN)" ""
            prompt_var "ADMIN_IDS" "Telegram ID администраторов через запятую (ADMIN_IDS)" ""
            prompt_var "TRUSTED_ADMIN_IPS" "Белый список IP-адресов администратора (вход с этих IP не будет вызывать тревогу, например: 192.168.1.50, через запятую)" "${TRUSTED_IPS_DEFAULT}"
            prompt_var "PROXMOX_HOST" "IP и порт вашего хоста Proxmox VE (PROXMOX_HOST)" "${PVE_HOST_DEFAULT}"
            prompt_var "PROXMOX_USER" "Имя пользователя Proxmox (PROXMOX_USER)" "root@pam"
            
            if [ -n "${AUTO_TOKEN_ID}" ] && [ -n "${AUTO_TOKEN_SECRET}" ]; then
                # Записываем сгенерированный или выбранный токен напрямую в .env без лишних вопросов
                if grep -q "^PROXMOX_TOKEN_ID=" "${ENV_FILE}"; then
                    sed -i "s/^PROXMOX_TOKEN_ID=.*/PROXMOX_TOKEN_ID=${AUTO_TOKEN_ID}/" "${ENV_FILE}"
                else
                    echo "PROXMOX_TOKEN_ID=${AUTO_TOKEN_ID}" >> "${ENV_FILE}"
                fi
                if grep -q "^PROXMOX_TOKEN_SECRET=" "${ENV_FILE}"; then
                    sed -i "s/^PROXMOX_TOKEN_SECRET=.*/PROXMOX_TOKEN_SECRET=${AUTO_TOKEN_SECRET}/" "${ENV_FILE}"
                else
                    echo "PROXMOX_TOKEN_SECRET=${AUTO_TOKEN_SECRET}" >> "${ENV_FILE}"
                fi
                echo -e "   ${GREEN}✓ Успешно использован API-токен: PROXMOX_TOKEN_ID=${AUTO_TOKEN_ID}${NC}"
            else
                prompt_var "PROXMOX_TOKEN_ID" "Proxmox API Token ID (PROXMOX_TOKEN_ID)" ""
                prompt_var "PROXMOX_TOKEN_SECRET" "Proxmox API Token Secret (PROXMOX_TOKEN_SECRET)" ""
            fi
            
            # Запрашиваем VPN_VMID
            prompt_var "VPN_VMID" "Идентификатор контейнера с VPN (VPN_VMID)" "${AUTO_VPN_VMID:-101}"
            
            # Мониторинг VPS
            prompt_bool "REMOTE_MONITOR_ENABLE" "Включить мониторинг удаленного сервера VPS?" "False"
            vps_enabled=$(grep -E "^REMOTE_MONITOR_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
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
            prompt_bool "ENABLE_FREE_PROXY_ROTATION" "Включить автоматическую ротацию бесплатных прокси при сбое?" "False"
        
            # Мониторинг роутера через SSH conntrack/iptables
            prompt_bool "ROUTER_MONITOR_ENABLE" "Включить мониторинг трафика роутера через SSH?" "False"
            router_enabled=$(grep -E "^ROUTER_MONITOR_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
            if [ "${router_enabled}" = "true" ] || [ "${router_enabled}" = "1" ] || [ "${router_enabled}" = "y" ] || [ "${router_enabled}" = "yes" ]; then
                while true; do
                    # 1. Сначала опрашиваем параметры подключения для проведения теста
                    prompt_var "ROUTER_SSH_HOST" "IP-адрес SSH роутера (ROUTER_SSH_HOST)" "192.168.1.1"
                    prompt_var "ROUTER_SSH_PORT" "Порт SSH роутера (ROUTER_SSH_PORT)" "22"
                    prompt_var "ROUTER_SSH_USER" "Имя пользователя SSH роутера (ROUTER_SSH_USER)" "root"
                    
                    local current_pass=""
                    local current_key=""
                    if [ -f "${ENV_FILE}" ]; then
                        current_pass=$(grep -E "^ROUTER_SSH_PASSWORD=" "${ENV_FILE}" | cut -d'=' -f2-)
                        current_key=$(grep -E "^ROUTER_SSH_KEY=" "${ENV_FILE}" | cut -d'=' -f2-)
                    fi

                    local default_method="1"
                    if [ -z "${current_pass}" ] && [ -n "${current_key}" ] && [ "${current_key}" != "config/id_rsa_router" ]; then
                        default_method="2"
                    fi

                    echo -e "\n${BLUE}👉 Выберите метод авторизации на роутере:${NC}"
                    echo -e "   1) По паролю (ROUTER_SSH_PASSWORD)"
                    echo -e "   2) По SSH-ключу (ROUTER_SSH_KEY)"
                    read -rp "   Выберите вариант (1 или 2) [по умолчанию: ${default_method}]: " auth_method
                    if [ -z "${auth_method}" ]; then
                        auth_method="${default_method}"
                    fi

                    if [ "${auth_method}" = "2" ]; then
                        # Сбрасываем пароль в .env
                        local tmp_file="${ENV_FILE}.tmp"
                        while IFS= read -r line || [ -n "$line" ]; do
                            if [[ "$line" =~ ^ROUTER_SSH_PASSWORD= ]]; then
                                printf "%s\n" "ROUTER_SSH_PASSWORD=" >> "$tmp_file"
                            else
                                printf "%s\n" "$line" >> "$tmp_file"
                            fi
                        done < "${ENV_FILE}"
                        mv "$tmp_file" "${ENV_FILE}"

                        prompt_var "ROUTER_SSH_KEY" "Путь к приватному SSH ключу роутера (ROUTER_SSH_KEY)" "config/id_rsa_router"
                    else
                        # Сбрасываем ключ в .env
                        local tmp_file="${ENV_FILE}.tmp"
                        while IFS= read -r line || [ -n "$line" ]; do
                            if [[ "$line" =~ ^ROUTER_SSH_KEY= ]]; then
                                printf "%s\n" "ROUTER_SSH_KEY=" >> "$tmp_file"
                            else
                                printf "%s\n" "$line" >> "$tmp_file"
                            fi
                        done < "${ENV_FILE}"
                        mv "$tmp_file" "${ENV_FILE}"

                        prompt_var "ROUTER_SSH_PASSWORD" "Пароль SSH роутера (ROUTER_SSH_PASSWORD)" ""
                    fi

                    prompt_var "ROUTER_TYPE" "Тип операционной системы роутера (openwrt/keenetic/generic)" "openwrt"
                    
                    # Временно записываем ROUTER_MONITOR_ENABLE=True для корректного считывания тестовым скриптом
                    sed -i "s/^ROUTER_MONITOR_ENABLE=.*/ROUTER_MONITOR_ENABLE=True/" "${ENV_FILE}"
        
                    # 2. Выполняем предварительное автотестирование, выбор режима и автоустановку
                    echo -e "\n${YELLOW}Запуск диагностики доступности роутера и выбора режима мониторинга...${NC}"
                    if "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/setup_modules/test_router_only.py"; then
                        echo -e "${GREEN}✓ Диагностика, выбор режима и настройка роутера завершены успешно!${NC}"
                        break
                    else
                        echo -e "${RED}❌ Не удалось подключиться к роутеру по SSH.${NC}"
                        echo -e "Хотите скорректировать параметры подключения по SSH и попробовать снова? (y/n) [y]"
                        read -rp ">> " retry_ssh
                        if [ -z "${retry_ssh}" ] || [ "${retry_ssh}" = "y" ] || [ "${retry_ssh}" = "Y" ]; then
                            echo -e "${YELLOW}Повторный ввод параметров SSH...${NC}"
                            continue
                        else
                            echo -e "${YELLOW}⚠️ Вы решили пропустить перенастройку. Вы можете отредактировать параметры мониторинга в .env вручную.${NC}"
                            break
                        fi
                    fi
                done
                
                prompt_bool "ROUTER_AUTO_BAN" "Включить автоматический бан нарушителей на роутере?" "False"
                prompt_var "ROUTER_MAX_VIOLATIONS" "Лимит попыток доступа до автоблокировки (ROUTER_MAX_VIOLATIONS)" "3"
            fi
        
            ENV_CREATED=0 # Сбрасываем предупреждение, так как переменные заполнены!
            echo -e "\n${GREEN}🎉 Конфигурация .env успешно завершена!${NC}"
        else
            echo -e "\n${YELLOW}⚠️ Интерактивная настройка пропущена. Отредактируйте .env вручную.${NC}"
        fi
    fi
}
