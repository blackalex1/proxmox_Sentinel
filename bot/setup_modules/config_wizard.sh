#!/usr/bin/env bash

# Run interactive environment configuration wizard
run_config_wizard() {
    print_lang "\n${YELLOW}[4/5] Настройка файла .env...${NC}" "\n${YELLOW}[4/5] Configuring .env file...${NC}"
    mkdir -p "${SCRIPT_DIR}/config"
    ENV_FILE="${SCRIPT_DIR}/config/.env"
    ENV_CREATED=0

    ENV_EXISTS=0
    ENV_WAS_PRESENT=0
    if [ ! -f "${ENV_FILE}" ]; then
        if [ -f "${SCRIPT_DIR}/config/.env.example" ]; then
            cp "${SCRIPT_DIR}/config/.env.example" "${ENV_FILE}"
            print_lang "${YELLOW}⚠️ Создан файл .env из шаблона config/.env.example.${NC}" "${YELLOW}⚠️ Created .env file from template config/.env.example.${NC}"
            ENV_CREATED=1
        else
            print_lang "${RED}❌ Ошибка: Шаблон config/.env.example не найден. Создаем новый файл .env...${NC}" "${RED}❌ Error: Template config/.env.example not found. Creating new .env file...${NC}"
            touch "${ENV_FILE}"
        fi
    else
        print_lang "${GREEN}✓ Файл конфигурации .env уже существует.${NC}" "${GREEN}✓ Configuration file .env already exists.${NC}"
        print_lang "Хотите перезапустить интерактивный мастер настройки и обновить .env? (y/n) [n]" "Do you want to rerun the interactive setup wizard and update .env? (y/n) [n]"
        read -rp ">> " rerun_wizard
        if [ "${rerun_wizard}" = "y" ] || [ "${rerun_wizard}" = "Y" ]; then
            ENV_EXISTS=0
            ENV_WAS_PRESENT=1
        else
            ENV_EXISTS=1
        fi
    fi

    # Automatically write/update BOT_LANGUAGE in .env based on INSTALL_LANG
    if [ -f "${ENV_FILE}" ]; then
        if grep -q "^BOT_LANGUAGE=" "${ENV_FILE}"; then
            sed -i "s/^BOT_LANGUAGE=.*/BOT_LANGUAGE=${INSTALL_LANG}/" "${ENV_FILE}"
        else
            echo "BOT_LANGUAGE=${INSTALL_LANG}" >> "${ENV_FILE}"
        fi
    fi

    if [ ${ENV_EXISTS} -eq 0 ]; then
        echo -e "\n${MAGENTA}==================================================${NC}"
        print_lang "${MAGENTA}   ИНТЕРАКТИВНЫЙ МАСТЕР НАСТРОЙКИ КОНФИГУРАЦИИ .env${NC}" "${MAGENTA}   INTERACTIVE .env CONFIGURATION WIZARD${NC}"
        echo -e "${MAGENTA}==================================================${NC}"
        print_lang "Вы можете настроить бота прямо сейчас. Если вы нажмете Enter,\nбудет сохранено текущее или дефолтное значение." "You can configure the bot right now. If you press Enter,\nthe current or default value will be saved."

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
            print_lang "\n${CYAN}Обнаружен ваш IP-адрес подключения по SSH: ${YELLOW}${DETECTED_SSH_IP}${NC}" "\n${CYAN}Detected your SSH connection IP address: ${YELLOW}${DETECTED_SSH_IP}${NC}"
            print_lang "Добавить его в белый список доверенных IP (TRUSTED_ADMIN_IPS)? (y/n) [y]" "Add it to the trusted IP whitelist (TRUSTED_ADMIN_IPS)? (y/n) [y]"
            read -rp ">> " add_ssh_ip
            if [ -z "${add_ssh_ip}" ] || [ "${add_ssh_ip}" = "y" ] || [ "${add_ssh_ip}" = "Y" ]; then
                TRUSTED_IPS_DEFAULT="${DETECTED_SSH_IP}"
            fi
        fi

        # 3. Автогенерация или использование существующего API-токена Proxmox через pveum
        AUTO_TOKEN_ID=""
        AUTO_TOKEN_SECRET=""
        SKIP_PROXMOX_SETUP=0
        
        PYTHON_EXEC="python3"
        if [ -f "${SCRIPT_DIR}/venv/bin/python" ]; then
            PYTHON_EXEC="${SCRIPT_DIR}/venv/bin/python"
        fi

        # Считываем уже существующий токен и настройки из .env
        EXISTING_HOST=""
        EXISTING_USER=""
        EXISTING_TOKEN_ID=""
        EXISTING_TOKEN_SECRET=""
        EXISTING_VERIFY_SSL="False"
        if [ -f "${ENV_FILE}" ]; then
            EXISTING_HOST=$(grep -E "^PROXMOX_HOST=" "${ENV_FILE}" | cut -d'=' -f2- | tr -d '\r\n ' || true)
            EXISTING_USER=$(grep -E "^PROXMOX_USER=" "${ENV_FILE}" | cut -d'=' -f2- | tr -d '\r\n ' || true)
            EXISTING_TOKEN_ID=$(grep -E "^PROXMOX_TOKEN_ID=" "${ENV_FILE}" | cut -d'=' -f2- | tr -d '\r\n ' || true)
            EXISTING_TOKEN_SECRET=$(grep -E "^PROXMOX_TOKEN_SECRET=" "${ENV_FILE}" | cut -d'=' -f2- | tr -d '\r\n ' || true)
            EXISTING_VERIFY_SSL=$(grep -E "^PROXMOX_VERIFY_SSL=" "${ENV_FILE}" | cut -d'=' -f2- | tr -d '\r\n ' || true)
            if [ -z "${EXISTING_VERIFY_SSL}" ]; then
                EXISTING_VERIFY_SSL="False"
            fi
        fi

        # Если в .env есть все настройки Proxmox, попробуем их проверить (игнорируя плейсхолдеры из примера)
        if [ -n "${EXISTING_HOST}" ] && [ "${EXISTING_HOST}" != "your_proxmox_ip:8006" ] && [ "${EXISTING_HOST}" != "your_proxmox_ip" ] && \
           [ -n "${EXISTING_USER}" ] && \
           [ -n "${EXISTING_TOKEN_ID}" ] && [ "${EXISTING_TOKEN_ID}" != "root@pam!MyToken" ] && \
           [ -n "${EXISTING_TOKEN_SECRET}" ] && [ "${EXISTING_TOKEN_SECRET}" != "ваш_секретный_код_токена" ]; then
            print_lang "\n${CYAN}Обнаружена существующая конфигурация Proxmox в .env.${NC}" "\n${CYAN}Found existing Proxmox configuration in .env.${NC}"
            print_lang "Проверка подключения к Proxmox VE API..." "Checking connection to Proxmox VE API..."
            
            TEST_OUT=$(${PYTHON_EXEC} -c "
import sys
from proxmoxer import ProxmoxAPI
try:
    host = sys.argv[1]
    user = sys.argv[2]
    token_id = sys.argv[3]
    token_secret = sys.argv[4]
    verify_ssl = sys.argv[5].lower() == 'true'
    
    token_name = token_id.split('!')[1] if '!' in token_id else token_id
    proxmox = ProxmoxAPI(host, user=user, token_name=token_name, token_value=token_secret, verify_ssl=verify_ssl)
    proxmox.nodes.get()
    print('SUCCESS')
except Exception as e:
    print('ERROR:', e)
" "${EXISTING_HOST}" "${EXISTING_USER}" "${EXISTING_TOKEN_ID}" "${EXISTING_TOKEN_SECRET}" "${EXISTING_VERIFY_SSL}" 2>/dev/null || echo "FAILED")
            
            TEST_OUT=$(echo "${TEST_OUT}" | tr -d '\r\n')
            if [ "${TEST_OUT}" = "SUCCESS" ]; then
                print_lang "${GREEN}✓ Подключение к Proxmox VE API успешно проверено! Валидный токен.${NC}" "${GREEN}✓ Connection to Proxmox VE API verified successfully! Valid token.${NC}"
                print_lang "Хотите использовать существующие настройки Proxmox и пропустить их изменение? (y/n) [y]" "Do you want to use existing Proxmox settings and skip changing them? (y/n) [y]"
                read -rp ">> " skip_pve_ask
                if [ -z "${skip_pve_ask}" ] || [ "${skip_pve_ask}" = "y" ] || [ "${skip_pve_ask}" = "Y" ]; then
                    AUTO_TOKEN_ID="${EXISTING_TOKEN_ID}"
                    AUTO_TOKEN_SECRET="${EXISTING_TOKEN_SECRET}"
                    SKIP_PROXMOX_SETUP=1
                fi
            else
                print_lang "${RED}⚠️ Существующие учетные данные Proxmox не прошли проверку: ${TEST_OUT}${NC}" "${RED}⚠️ Existing Proxmox credentials failed validation: ${TEST_OUT}${NC}"
            fi
        fi

        if [ ${SKIP_PROXMOX_SETUP} -eq 0 ]; then
            if command -v pveum >/dev/null 2>&1; then
                print_lang "\n${GREEN}✓ Обнаружен Proxmox VE (утилита pveum доступна).${NC}" "\n${GREEN}✓ Proxmox VE detected (pveum utility is available).${NC}"
                
                # Получаем список существующих токенов для root@pam
                TOKENS_JSON=$(pveum user token list root@pam --output-format json 2>/dev/null || echo "[]")
                # Парсим имена токенов через Python
                EXISTING_TOKENS=$(python3 -c "import sys, json; tokens = json.loads(sys.stdin.read()); print(','.join([t.get('tokenid', '') for t in tokens if 'tokenid' in t]))" <<< "${TOKENS_JSON}" 2>/dev/null || true)
                EXISTING_TOKENS=$(echo "${EXISTING_TOKENS}" | tr -d '\r\n ' || true)
                
                token_choice="new"
                if [ -n "${EXISTING_TOKENS}" ]; then
                    print_lang "${CYAN}Обнаружены существующие API-токены Proxmox для пользователя root@pam:${NC}" "${CYAN}Found existing Proxmox API tokens for user root@pam:${NC}"
                    IFS=',' read -r -a token_array <<< "${EXISTING_TOKENS}"
                    for i in "${!token_array[@]}"; do
                        token_array[i]=$(echo "${token_array[i]}" | tr -d '\r\n ')
                        echo -e "  $((i+1))) root@pam!${token_array[i]}"
                    done
                    print_lang "  $(( ${#token_array[@]} + 1 ))) [Создать новый API-токен]" "  $(( ${#token_array[@]} + 1 ))) [Create new API token]"
                    
                    print_lang "\n${YELLOW}Выберите номер токена для использования (или создайте новый):${NC}" "\n${YELLOW}Select token number to use (or create a new one):${NC}"
                    read -rp ">> " user_token_selection
                    
                    # Проверяем корректность выбора
                    if [[ "$user_token_selection" =~ ^[0-9]+$ ]] && [ "$user_token_selection" -ge 1 ] && [ "$user_token_selection" -le "${#token_array[@]}" ]; then
                        selected_token_name="${token_array[$((user_token_selection-1))]}"
                        selected_token_name=$(echo "${selected_token_name}" | tr -d '\r\n ')
                        AUTO_TOKEN_ID="root@pam!${selected_token_name}"
                        print_lang "${GREEN}✓ Выбран существующий токен: ${AUTO_TOKEN_ID}${NC}" "${GREEN}✓ Selected existing token: ${AUTO_TOKEN_ID}${NC}"
                        
                        if [ "${AUTO_TOKEN_ID}" = "${EXISTING_TOKEN_ID}" ] && [ -n "${EXISTING_TOKEN_SECRET}" ]; then
                            # Проверяем валидность этого сохраненного секрета
                            print_lang "Проверка подключения к Proxmox VE с сохраненным секретом..." "Checking connection to Proxmox VE with saved secret..."
                            TEST_HOST="${EXISTING_HOST}"
                            if [ -z "${TEST_HOST}" ]; then
                                TEST_HOST="${PVE_HOST_DEFAULT}"
                            fi
                            TEST_USER="${EXISTING_USER}"
                            if [ -z "${TEST_USER}" ]; then
                                TEST_USER="root@pam"
                            fi
                            TEST_OUT=$(${PYTHON_EXEC} -c "
import sys
from proxmoxer import ProxmoxAPI
try:
    host = sys.argv[1]
    user = sys.argv[2]
    token_id = sys.argv[3]
    token_secret = sys.argv[4]
    verify_ssl = sys.argv[5].lower() == 'true'
    
    token_name = token_id.split('!')[1] if '!' in token_id else token_id
    proxmox = ProxmoxAPI(host, user=user, token_name=token_name, token_value=token_secret, verify_ssl=verify_ssl)
    proxmox.nodes.get()
    print('SUCCESS')
except Exception as e:
    print('ERROR:', e)
" "${TEST_HOST}" "${TEST_USER}" "${AUTO_TOKEN_ID}" "${EXISTING_TOKEN_SECRET}" "${EXISTING_VERIFY_SSL}" 2>/dev/null || echo "FAILED")
                            
                            TEST_OUT=$(echo "${TEST_OUT}" | tr -d '\r\n')
                            if [ "${TEST_OUT}" = "SUCCESS" ]; then
                                AUTO_TOKEN_SECRET="${EXISTING_TOKEN_SECRET}"
                                print_lang "${GREEN}✓ Обнаружен сохраненный секрет для этого токена в .env, и подключение успешно проверено. Используем его автоматически.${NC}" "${GREEN}✓ Found saved secret for this token in .env, and connection verified successfully. Using it automatically.${NC}"
                            else
                                print_lang "${RED}⚠️ Сохраненный секрет из .env не прошел проверку подключения: ${TEST_OUT}${NC}" "${RED}⚠️ Saved secret from .env failed connection check: ${TEST_OUT}${NC}"
                                print_lang "${BLUE}👉 Введите секретный код (Secret Value) для этого токена:${NC}" "${BLUE}👉 Enter the secret key (Secret Value) for this token:${NC}"
                                read -rp ">> " AUTO_TOKEN_SECRET
                                AUTO_TOKEN_SECRET=$(echo "${AUTO_TOKEN_SECRET}" | tr -d '\r\n ')
                            fi
                        else
                            print_lang "${BLUE}👉 Введите секретный код (Secret Value) для этого токена:${NC}" "${BLUE}👉 Enter the secret key (Secret Value) for this token:${NC}"
                            read -rp ">> " AUTO_TOKEN_SECRET
                            AUTO_TOKEN_SECRET=$(echo "${AUTO_TOKEN_SECRET}" | tr -d '\r\n ')
                        fi
                        token_choice="existing"
                    else
                        token_choice="new"
                    fi
                fi
                
                if [ "${token_choice}" = "new" ]; then
                    print_lang "\nХотите ли вы автоматически сгенерировать новый выделенный API-токен для работы бота? (y/n) [y]" "\nDo you want to automatically generate a new dedicated API token for the bot? (y/n) [y]"
                    read -rp ">> " generate_token_pve
                    if [ -z "${generate_token_pve}" ] || [ "${generate_token_pve}" = "y" ] || [ "${generate_token_pve}" = "Y" ]; then
                        print_lang "Введите имя нового токена [по умолчанию: aegis-ips]:" "Enter new token name [default: aegis-ips]:"
                        read -rp ">> " new_token_name
                        if [ -z "${new_token_name}" ]; then
                            new_token_name="aegis-ips"
                        fi
                        
                        print_lang "Генерация API-токена 'root@pam!${new_token_name}'..." "Generating API token 'root@pam!${new_token_name}'..."
                        # Удаляем старый токен с таким же именем, если он был
                        pveum user token delete root@pam "${new_token_name}" 2>/dev/null || true
                        # Создаем новый токен
                        TOKEN_OUT=$(pveum user token add root@pam "${new_token_name}" --privsep 0 --output-format json 2>/dev/null || true)
                        if [ -n "${TOKEN_OUT}" ]; then
                            TOKEN_SECRET=$(python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('value', ''))" <<< "${TOKEN_OUT}" 2>/dev/null || true)
                            if [ -n "${TOKEN_SECRET}" ]; then
                                print_lang "${GREEN}✓ API-токен успешно сгенерирован!${NC}" "${GREEN}✓ API token generated successfully!${NC}"
                                AUTO_TOKEN_ID="root@pam!${new_token_name}"
                                AUTO_TOKEN_SECRET="${TOKEN_SECRET}"
                            else
                                print_lang "${RED}⚠️ Не удалось извлечь секрет токена из вывода pveum.${NC}" "${RED}⚠️ Failed to extract token secret from pveum output.${NC}"
                            fi
                        else
                            print_lang "${RED}⚠️ Ошибка при создании токена через pveum.${NC}" "${RED}⚠️ Error creating token via pveum.${NC}"
                        fi
                    fi
                fi
            fi
        fi

        # 4. Автоопределение LXC контейнеров для VPN_VMID и Spectre Panel
        AUTO_VPN_VMID=""
        DETECTED_PANELS_JSON=""
        USE_AUTO_PANEL="n"
        SP_JSON="[]"
        
        local setup_vpn_lxc="y"
        print_lang "Хотите ли вы настроить мониторинг локального VPN-контейнера на этом Proxmox VE? (y/n) [y]" "Do you want to configure monitoring for a local VPN container on this Proxmox VE? (y/n) [y]"
        read -rp ">> " setup_vpn_lxc_input
        if [ "${setup_vpn_lxc_input}" = "n" ] || [ "${setup_vpn_lxc_input}" = "N" ]; then
            setup_vpn_lxc="n"
            AUTO_VPN_VMID="0"
        fi
        
        if [ "${setup_vpn_lxc}" = "y" ]; then
            # Мы можем попробовать найти Spectre Panel прямо сейчас, до вывода списка всех LXC
            print_lang "\n${CYAN}Поиск установленных панелей Spectre Panel на LXC контейнерах...${NC}" "\n${CYAN}Searching for installed Spectre Panels on LXC containers...${NC}"
            if [ -f "${SCRIPT_DIR}/venv/bin/python" ]; then
                DETECTED_PANELS_JSON=$(BOT_TOKEN="123:abc" "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/setup_modules/detect_panels.py" 2>/dev/null || true)
            else
                DETECTED_PANELS_JSON=$(BOT_TOKEN="123:abc" python3 "${SCRIPT_DIR}/setup_modules/detect_panels.py" 2>/dev/null || true)
            fi
            
            PANEL_VMID_SUGGESTION=""
            PANEL_URL_SUGGESTION=""
            PANEL_NAME_SUGGESTION=""
            
            if [ -n "${DETECTED_PANELS_JSON}" ] && [ "${DETECTED_PANELS_JSON}" != "[]" ]; then
                PANEL_VMID_SUGGESTION=$(python3 -c "import sys, json; panels = json.loads(sys.argv[1]); p = panels[0] if panels else {}; url = p.get('url', ''); name = p.get('name', ''); import re; m = re.search(r'LXC (\d+)', name); print(m.group(1) if m else '')" "${DETECTED_PANELS_JSON}" 2>/dev/null || true)
                PANEL_URL_SUGGESTION=$(python3 -c "import sys, json; panels = json.loads(sys.argv[1]); p = panels[0] if panels else {}; print(p.get('url', ''))" "${DETECTED_PANELS_JSON}" 2>/dev/null || true)
                PANEL_NAME_SUGGESTION=$(python3 -c "import sys, json; panels = json.loads(sys.argv[1]); p = panels[0] if panels else {}; print(p.get('name', ''))" "${DETECTED_PANELS_JSON}" 2>/dev/null || true)
            fi
            
            if [ -n "${PANEL_VMID_SUGGESTION}" ]; then
                print_lang "${GREEN}✓ Обнаружена установленная Spectre Panel: ${YELLOW}${PANEL_NAME_SUGGESTION}${GREEN} (${PANEL_URL_SUGGESTION})${NC}" "${GREEN}✓ Detected installed Spectre Panel: ${YELLOW}${PANEL_NAME_SUGGESTION}${GREEN} (${PANEL_URL_SUGGESTION})${NC}"
                print_lang "Использовать этот контейнер (${YELLOW}${PANEL_VMID_SUGGESTION}${NC}) для мониторинга VPN_VMID и автоматически подключить панель? (y/n) [y]" "Use this container (${YELLOW}${PANEL_VMID_SUGGESTION}${NC}) for VPN_VMID monitoring and automatically connect the panel? (y/n) [y]"
                read -rp ">> " use_auto_panel_input
                if [ -z "${use_auto_panel_input}" ] || [ "${use_auto_panel_input}" = "y" ] || [ "${use_auto_panel_input}" = "Y" ]; then
                    USE_AUTO_PANEL="y"
                    AUTO_VPN_VMID="${PANEL_VMID_SUGGESTION}"
                    SP_JSON="${DETECTED_PANELS_JSON}"
                    print_lang "${GREEN}✓ Выбран контейнер с панелью: ${AUTO_VPN_VMID}${NC}" "${GREEN}✓ Selected container with panel: ${AUTO_VPN_VMID}${NC}"
                fi
            fi
            
            if [ "${USE_AUTO_PANEL}" = "n" ]; then
                if command -v pct >/dev/null 2>&1; then
                    print_lang "\n${CYAN}Поиск контейнеров LXC на хосте Proxmox VE...${NC}" "\n${CYAN}Searching for LXC containers on Proxmox VE host...${NC}"
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
                                if [[ "$lower_name" =~ vpn || "$lower_name" =~ wg || "$lower_name" =~ wireguard || "$lower_name" =~ openvpn || "$lower_name" =~ xray || "$lower_name" =~ spectre || "$lower_name" =~ panel || "$lower_name" =~ x-ui || "$lower_name" =~ xui ]]; then
                                    if [ $auto_idx -eq -1 ]; then
                                        auto_idx=$idx
                                    fi
                                fi
                                idx=$((idx+1))
                            fi
                        done <<< "$LXC_LIST"
                        
                        if [ ${#vmid_array[@]} -gt 0 ]; then
                            print_lang "Найденные контейнеры LXC:" "Found LXC containers:"
                            for i in "${!vmid_array[@]}"; do
                                if [ $i -eq $auto_idx ]; then
                                    print_lang "  $((i+1))) ${GREEN}${vmid_array[i]} - ${name_array[i]} (Статус: ${status_array[i]}) [Автоопределение: VPN]${NC}" "  $((i+1))) ${GREEN}${vmid_array[i]} - ${name_array[i]} (Status: ${status_array[i]}) [Auto-detected: VPN]${NC}"
                                else
                                    print_lang "  $((i+1))) ${vmid_array[i]} - ${name_array[i]} (Статус: ${status_array[i]})" "  $((i+1))) ${vmid_array[i]} - ${name_array[i]} (Status: ${status_array[i]})"
                                fi
                            done
                            print_lang "  $(( ${#vmid_array[@]} + 1 ))) [Ввести ID вручную]" "  $(( ${#vmid_array[@]} + 1 ))) [Enter ID manually]"
                            
                            default_option=""
                            if [ $auto_idx -ne -1 ]; then
                                default_option=$((auto_idx+1))
                            fi
                            
                            if [ "${INSTALL_LANG}" = "ru" ]; then
                                echo -e "\n${YELLOW}Выберите порядковый номер из списка (1, 2...) или введите ID контейнера (например, 101) для VPN_VMID [по умолчанию: ${default_option:-ID вручную}]:${NC}"
                            else
                                echo -e "\n${YELLOW}Select sequence number from the list (1, 2...) or enter container ID (e.g., 101) for VPN_VMID [default: ${default_option:-manual ID}]:${NC}"
                            fi
                            read -rp ">> " user_lxc_selection
                            
                            if [ -z "$user_lxc_selection" ] && [ -n "$default_option" ]; then
                                user_lxc_selection=$default_option
                            fi
                            
                            if [[ "$user_lxc_selection" =~ ^[0-9]+$ ]]; then
                                # Сначала проверяем, не введен ли порядковый номер из списка
                                if [ "$user_lxc_selection" -ge 1 ] && [ "$user_lxc_selection" -le "${#vmid_array[@]}" ]; then
                                    AUTO_VPN_VMID="${vmid_array[$((user_lxc_selection-1))]}"
                                    print_lang "${GREEN}✓ Выбран контейнер: ${AUTO_VPN_VMID} (${name_array[$((user_lxc_selection-1))]})${NC}" "${GREEN}✓ Selected container: ${AUTO_VPN_VMID} (${name_array[$((user_lxc_selection-1))]})${NC}"
                                else
                                    # Иначе проверяем, не введен ли реальный VMID напрямую
                                    for i in "${!vmid_array[@]}"; do
                                        if [ "${vmid_array[i]}" -eq "$user_lxc_selection" ]; then
                                            AUTO_VPN_VMID="$user_lxc_selection"
                                            print_lang "${GREEN}✓ Выбран контейнер по прямому ID: ${AUTO_VPN_VMID} (${name_array[i]})${NC}" "${GREEN}✓ Selected container by direct ID: ${AUTO_VPN_VMID} (${name_array[i]})${NC}"
                                            break
                                        fi
                                    done
                                fi
                            fi
                        fi
                    fi
                fi
            fi
        fi
        
        local run_wizard="y"
        if [ ${ENV_WAS_PRESENT} -eq 0 ]; then
            print_lang "\n${YELLOW}Хотите ли вы настроить параметры .env интерактивно? (y/n) [y]${NC}" "\n${YELLOW}Do you want to configure .env parameters interactively? (y/n) [y]${NC}"
            read -rp ">> " run_wizard
        fi
        if [ -z "${run_wizard}" ] || [ "${run_wizard}" = "y" ] || [ "${run_wizard}" = "Y" ]; then
            # Запускаем интерактивный мастер
            prompt_var "BOT_TOKEN" "$(echo_lang "Токен вашего Telegram-бота (BOT_TOKEN)" "Your Telegram Bot Token (BOT_TOKEN)")" ""
            prompt_var "ADMIN_IDS" "$(echo_lang "Telegram ID администраторов через запятую (ADMIN_IDS)" "Telegram IDs of administrators, comma-separated (ADMIN_IDS)")" ""
            prompt_var "TRUSTED_ADMIN_IPS" "$(echo_lang "Белый список IP-адресов администратора (вход с этих IP не будет вызывать тревогу, например: 192.168.1.50, через запятую)" "Admin IP whitelist (connections from these IPs won't trigger alarms, e.g.: 192.168.1.50, comma-separated)")" "${TRUSTED_IPS_DEFAULT}"
            if [ ${SKIP_PROXMOX_SETUP} -eq 1 ]; then
                print_lang "   ${GREEN}✓ Настройка параметров подключения к Proxmox VE пропущена (параметры верны).${NC}" "   ${GREEN}✓ Proxmox VE connection parameters configuration skipped (parameters are correct).${NC}"
            else
                prompt_var "PROXMOX_HOST" "$(echo_lang "IP и порт вашего хоста Proxmox VE (PROXMOX_HOST)" "IP and port of your Proxmox VE host (PROXMOX_HOST)")" "${PVE_HOST_DEFAULT}"
                prompt_var "PROXMOX_USER" "$(echo_lang "Имя пользователя Proxmox (PROXMOX_USER)" "Proxmox username (PROXMOX_USER)")" "root@pam"
                
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
                    print_lang "   ${GREEN}✓ Успешно использован API-токен: PROXMOX_TOKEN_ID=${AUTO_TOKEN_ID}${NC}" "   ${GREEN}✓ Successfully used API token: PROXMOX_TOKEN_ID=${AUTO_TOKEN_ID}${NC}"
                else
                    prompt_var "PROXMOX_TOKEN_ID" "$(echo_lang "Proxmox API Token ID (PROXMOX_TOKEN_ID)" "Proxmox API Token ID (PROXMOX_TOKEN_ID)")" ""
                    prompt_var "PROXMOX_TOKEN_SECRET" "$(echo_lang "Proxmox API Token Secret (PROXMOX_TOKEN_SECRET)" "Proxmox API Token Secret (PROXMOX_TOKEN_SECRET)")" ""
                fi
            fi
            
            # Записываем VPN_VMID напрямую, если он был выбран на шаге автоопределения
            if [ "${AUTO_VPN_VMID}" = "0" ]; then
                if grep -q "^VPN_VMID=" "${ENV_FILE}"; then
                    sed -i "s/^VPN_VMID=.*/VPN_VMID=0/" "${ENV_FILE}"
                else
                    echo "VPN_VMID=0" >> "${ENV_FILE}"
                fi
                print_lang "   ${GREEN}✓ Мониторинг локального VPN-контейнера отключен (VPN_VMID=0).${NC}" "   ${GREEN}✓ Local VPN container monitoring is disabled (VPN_VMID=0).${NC}"
            elif [ -n "${AUTO_VPN_VMID}" ]; then
                if grep -q "^VPN_VMID=" "${ENV_FILE}"; then
                    sed -i "s/^VPN_VMID=.*/VPN_VMID=${AUTO_VPN_VMID}/" "${ENV_FILE}"
                else
                    echo "VPN_VMID=${AUTO_VPN_VMID}" >> "${ENV_FILE}"
                fi
                print_lang "   ${GREEN}✓ Успешно сохранен идентификатор контейнера: VPN_VMID=${AUTO_VPN_VMID}${NC}" "   ${GREEN}✓ Container ID saved successfully: VPN_VMID=${AUTO_VPN_VMID}${NC}"
            else
                prompt_var "VPN_VMID" "$(echo_lang "Идентификатор контейнера с VPN (VPN_VMID)" "VPN container ID (VPN_VMID)")" "101"
            fi
            
            # Мониторинг VPS
            prompt_bool "REMOTE_MONITOR_ENABLE" "$(echo_lang "Включить мониторинг удаленного сервера VPS?" "Enable target VPS monitoring?")" "False"
            vps_enabled=$(grep -E "^REMOTE_MONITOR_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
            if [ "${vps_enabled}" = "true" ] || [ "${vps_enabled}" = "1" ] || [ "${vps_enabled}" = "y" ] || [ "${vps_enabled}" = "yes" ]; then
                prompt_var "REMOTE_SERVER_IP" "$(echo_lang "IP-адрес удаленного сервера VPS (REMOTE_SERVER_IP)" "IP address of target VPS (REMOTE_SERVER_IP)")" ""
                prompt_var "REMOTE_SERVER_USER" "$(echo_lang "Имя пользователя SSH на VPS (REMOTE_SERVER_USER)" "SSH username on VPS (REMOTE_SERVER_USER)")" "root"
                prompt_var "REMOTE_SERVER_SSH_KEY" "$(echo_lang "Имя ключа или путь к приватному SSH ключу (REMOTE_SERVER_SSH_KEY)" "Key name or path to private SSH key (REMOTE_SERVER_SSH_KEY)")" "id_rsa_remote"
                prompt_var "REMOTE_MONITOR_IGNORE_KEYS" "$(echo_lang "Игнорировать успешные входы по SSH с данных ключей (через запятую)" "Ignore successful SSH logins from these keys (comma-separated)")" "bot@bot"
                prompt_var "REMOTE_MONITOR_IGNORE_IPS" "$(echo_lang "Игнорировать успешные входы по SSH с данных IP-адресов (через запятую)" "Ignore successful SSH logins from these IP addresses (comma-separated)")" ""
            fi
        
            # Интерактивная настройка Spectre Panel (автоопределение с ручным вводом при необходимости)
            print_lang "\n${BLUE}👉 Настройка Spectre Panel (управление VPN-клиентами):${NC}" "\n${BLUE}👉 Spectre Panel Setup (VPN client management):${NC}"
            
            local configure_spectre_manual="n"
            if [ "${USE_AUTO_PANEL}" = "y" ]; then
                print_lang "   ${GREEN}✓ Автоматически подключена обнаруженная панель (контейнер ${AUTO_VPN_VMID}).${NC}" "   ${GREEN}✓ Detected panel automatically connected (container ${AUTO_VPN_VMID}).${NC}"
                print_lang "Хотите ли вы дополнительно настроить еще одну панель вручную? (y/n) [n]" "Do you want to additionally configure another panel manually? (y/n) [n]"
                read -rp ">> " configure_spectre_manual
            else
                print_lang "Хотите ли вы настроить интеграцию с Spectre Panel? (y/n) [y]" "Do you want to configure integration with Spectre Panel? (y/n) [y]"
                read -rp ">> " setup_spectre_input
                if [ -z "${setup_spectre_input}" ] || [ "${setup_spectre_input}" = "y" ] || [ "${setup_spectre_input}" = "Y" ]; then
                    print_lang "${YELLOW}Запуск автоматического поиска установленных панелей...${NC}" "${YELLOW}Launching automatic search for installed panels...${NC}"
                    
                    DETECTED_JSON=""
                    if [ -f "${SCRIPT_DIR}/venv/bin/python" ]; then
                        DETECTED_JSON=$(BOT_TOKEN="123:abc" "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/setup_modules/detect_panels.py" 2>"${SCRIPT_DIR}/detect_panels.log" || true)
                    else
                        DETECTED_JSON=$(BOT_TOKEN="123:abc" python3 "${SCRIPT_DIR}/setup_modules/detect_panels.py" 2>"${SCRIPT_DIR}/detect_panels.log" || true)
                    fi
                    
                    PANELS_FOUND=0
                    if [ -n "${DETECTED_JSON}" ] && [ "${DETECTED_JSON}" != "[]" ]; then
                        PANELS_FOUND=1
                    fi
                    
                    USE_DETECTED="n"
                    if [ ${PANELS_FOUND} -eq 1 ]; then
                        print_lang "\n${GREEN}✓ Обнаружены следующие панели Spectre Panel:${NC}" "\n${GREEN}✓ Found the following Spectre Panels:${NC}"
                        python3 -c "import sys, json; panels = json.loads(sys.argv[1]); [print(f'  - {p[\"name\"]} ({p[\"url\"]})') for p in panels]" "${DETECTED_JSON}" 2>/dev/null || print_lang "  (Не удалось отформатировать вывод)" "  (Failed to format output)"
                        
                        print_lang "\nИспользовать обнаруженные панели? (y/n) [y]" "\nUse detected panels? (y/n) [y]"
                        read -rp ">> " use_detected_input
                        if [ -z "${use_detected_input}" ] || [ "${use_detected_input}" = "y" ] || [ "${use_detected_input}" = "Y" ]; then
                            USE_DETECTED="y"
                        fi
                    else
                        print_lang "\n${YELLOW}⚠️ Не удалось автоматически обнаружить установленные панели Spectre Panel.${NC}" "\n${YELLOW}⚠️ Failed to automatically detect installed Spectre Panels.${NC}"
                        if [ -f "${SCRIPT_DIR}/detect_panels.log" ] && [ -s "${SCRIPT_DIR}/detect_panels.log" ]; then
                            print_lang "${CYAN}Детали ошибки поиска:${NC}" "${CYAN}Search error details:${NC}"
                            cat "${SCRIPT_DIR}/detect_panels.log"
                        fi
                    fi
                    rm -f "${SCRIPT_DIR}/detect_panels.log"
                    
                    if [ "${USE_DETECTED}" = "y" ]; then
                        SP_JSON="${DETECTED_JSON}"
                        print_lang "Хотите ли вы дополнительно настроить еще одну панель вручную? (y/n) [n]" "Do you want to additionally configure another panel manually? (y/n) [n]"
                        read -rp ">> " configure_spectre_manual
                    else
                        print_lang "Хотите ли вы настроить адрес и API-токен Spectre Panel вручную? (y/n) [y]" "Do you want to configure Spectre Panel address and API token manually? (y/n) [y]"
                        read -rp ">> " configure_spectre_manual
                        if [ -z "${configure_spectre_manual}" ] || [ "${configure_spectre_manual}" = "y" ] || [ "${configure_spectre_manual}" = "Y" ]; then
                            configure_spectre_manual="y"
                        fi
                    fi
                fi
            fi
            
            if [ "${configure_spectre_manual}" = "y" ] || [ "${configure_spectre_manual}" = "Y" ]; then
                print_lang "\n${YELLOW}Введите параметры Spectre Panel:${NC}" "\n${YELLOW}Enter Spectre Panel parameters:${NC}"
                if [ "${INSTALL_LANG}" = "ru" ]; then
                    read -rp "Имя панели (например, Мой Сервер): " SP_NAME
                    read -rp "URL панели (например, http://10.10.10.101:2053): " SP_URL
                    read -rp "API Token панели: " SP_TOKEN
                    read -rp "Секретный путь панели (secret path, по умолчанию: ui): " SP_SECRET
                else
                    read -rp "Panel Name (e.g., My Server): " SP_NAME
                    read -rp "Panel URL (e.g., http://10.10.10.101:2053): " SP_URL
                    read -rp "Panel API Token: " SP_TOKEN
                    read -rp "Panel Secret Path (secret path, default: ui): " SP_SECRET
                fi
                if [ -z "${SP_SECRET}" ]; then
                    SP_SECRET="ui"
                fi
                
                if [ -n "${SP_URL}" ] && [ -n "${SP_TOKEN}" ]; then
                    # Объединяем с помощью python
                    SP_JSON=$(python3 -c "import sys, json; det = json.loads(sys.argv[1]); det.append({'name': sys.argv[2] or 'Manual Panel', 'url': sys.argv[3], 'token': sys.argv[4], 'secret_path': sys.argv[5]}); print(json.dumps(det))" "${SP_JSON}" "${SP_NAME}" "${SP_URL}" "${SP_TOKEN}" "${SP_SECRET}")
                    print_lang "${GREEN}✓ Параметры сохранены!${NC}" "${GREEN}✓ Parameters saved!${NC}"
                else
                    print_lang "${RED}⚠️ Не заполнены URL или Токен. Пропускаем ручную настройку панели.${NC}" "${RED}⚠️ URL or Token is missing. Skipping manual panel configuration.${NC}"
                fi
            fi
            
            # Записываем в .env
            if [ "${SP_JSON}" != "[]" ]; then
                if grep -q "^SPECTRE_PANELS=" "${ENV_FILE}"; then
                    sed -i "s|^SPECTRE_PANELS=.*|SPECTRE_PANELS='${SP_JSON}'|" "${ENV_FILE}"
                else
                    echo "SPECTRE_PANELS='${SP_JSON}'" >> "${ENV_FILE}"
                fi
                print_lang "${GREEN}✓ Настройки Spectre Panel успешно сохранены в .env файл.${NC}" "${GREEN}✓ Spectre Panel settings successfully saved to .env file.${NC}"
            fi

            # Настройки прокси для Telegram
            prompt_var "PROXY_URL" "$(echo_lang "Прокси для Telegram (PROXY_URL, оставьте пустым если не требуется)" "Proxy for Telegram (PROXY_URL, leave empty if not required)")" "${INSTALL_PROXY}"
            prompt_bool "ENABLE_FREE_PROXY_ROTATION" "$(echo_lang "Включить автоматическую ротацию бесплатных прокси при сбое?" "Enable automatic free proxy rotation on failure?")" "False"
        
            # Мониторинг роутера через SSH conntrack/iptables
            prompt_bool "ROUTER_MONITOR_ENABLE" "$(echo_lang "Включить мониторинг трафика роутера через SSH?" "Enable router traffic monitoring via SSH?")" "False"
            router_enabled=$(grep -E "^ROUTER_MONITOR_ENABLE=" "${ENV_FILE}" | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')
            if [ "${router_enabled}" = "true" ] || [ "${router_enabled}" = "1" ] || [ "${router_enabled}" = "y" ] || [ "${router_enabled}" = "yes" ]; then
                while true; do
                    # 1. Сначала опрашиваем параметры подключения для проведения теста
                    prompt_var "ROUTER_SSH_HOST" "$(echo_lang "IP-адрес SSH роутера (ROUTER_SSH_HOST)" "Router SSH IP address (ROUTER_SSH_HOST)")" "192.168.1.1"
                    prompt_var "ROUTER_SSH_PORT" "$(echo_lang "Порт SSH роутера (ROUTER_SSH_PORT)" "Router SSH port (ROUTER_SSH_PORT)")" "22"
                    prompt_var "ROUTER_SSH_USER" "$(echo_lang "Имя пользователя SSH роутера (ROUTER_SSH_USER)" "Router SSH username (ROUTER_SSH_USER)")" "root"
                    
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

                    print_lang "\n${BLUE}👉 Выберите метод авторизации на роутере:${NC}" "\n${BLUE}👉 Select router authorization method:${NC}"
                    print_lang "   1) По паролю (ROUTER_SSH_PASSWORD)" "   1) By password (ROUTER_SSH_PASSWORD)"
                    print_lang "   2) По SSH-ключу (ROUTER_SSH_KEY)" "   2) By SSH key (ROUTER_SSH_KEY)"
                    if [ "${INSTALL_LANG}" = "ru" ]; then
                        read -rp "   Выберите вариант (1 или 2) [по умолчанию: ${default_method}]: " auth_method
                    else
                        read -rp "   Select option (1 or 2) [default: ${default_method}]: " auth_method
                    fi
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

                        prompt_var "ROUTER_SSH_KEY" "$(echo_lang "Путь к приватному SSH ключу роутера (ROUTER_SSH_KEY)" "Path to router private SSH key (ROUTER_SSH_KEY)")" "config/id_rsa_router"
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

                        prompt_var "ROUTER_SSH_PASSWORD" "$(echo_lang "Пароль SSH роутера (ROUTER_SSH_PASSWORD)" "Router SSH password (ROUTER_SSH_PASSWORD)")" ""
                    fi

                    prompt_var "ROUTER_TYPE" "$(echo_lang "Тип операционной системы роутера (openwrt/keenetic/generic)" "Router operating system type (openwrt/keenetic/generic)")" "openwrt"
                    
                    # Временно записываем ROUTER_MONITOR_ENABLE=True для корректного считывания тестовым скриптом
                    sed -i "s/^ROUTER_MONITOR_ENABLE=.*/ROUTER_MONITOR_ENABLE=True/" "${ENV_FILE}"
        
                    # 2. Выполняем предварительное автотестирование, выбор режима и автоустановку
                    print_lang "\n${YELLOW}Запуск диагностики доступности роутера и выбора режима мониторинга...${NC}" "\n${YELLOW}Launching router availability diagnostics and monitoring mode selection...${NC}"
                    if "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/setup_modules/test_router_only.py"; then
                        print_lang "${GREEN}✓ Диагностика, выбор режима и настройка роутера завершены успешно!${NC}" "${GREEN}✓ Diagnostics, mode selection, and router setup completed successfully!${NC}"
                        break
                    else
                        print_lang "${RED}❌ Не удалось подключиться к роутеру по SSH.${NC}" "${RED}❌ Failed to connect to the router via SSH.${NC}"
                        print_lang "Хотите скорректировать параметры подключения по SSH и попробовать снова? (y/n) [y]" "Do you want to adjust SSH connection parameters and try again? (y/n) [y]"
                        read -rp ">> " retry_ssh
                        if [ -z "${retry_ssh}" ] || [ "${retry_ssh}" = "y" ] || [ "${retry_ssh}" = "Y" ]; then
                            print_lang "${YELLOW}Повторный ввод параметров SSH...${NC}" "${YELLOW}Re-entering SSH parameters...${NC}"
                            continue
                        else
                            print_lang "${YELLOW}⚠️ Вы решили пропустить перенастройку. Вы можете отредактировать параметры мониторинга в .env вручную.${NC}" "${YELLOW}⚠️ You chose to skip reconfiguration. You can edit the monitoring parameters in .env manually.${NC}"
                            break
                        fi
                    fi
                done
                
                prompt_bool "ROUTER_AUTO_BAN" "$(echo_lang "Включить автоматический бан нарушителей на роутере?" "Enable automatic ban of offenders on the router?")" "False"
                prompt_var "ROUTER_MAX_VIOLATIONS" "$(echo_lang "Лимит попыток доступа до автоблокировки (ROUTER_MAX_VIOLATIONS)" "Access attempts limit before auto-blocking (ROUTER_MAX_VIOLATIONS)")" "3"
            fi
        
            ENV_CREATED=0 # Сбрасываем предупреждение, так как переменные заполнены!
            print_lang "\n${GREEN}🎉 Конфигурация .env успешно завершена!${NC}" "\n${GREEN}🎉 .env configuration successfully completed!${NC}"
        else
            print_lang "\n${YELLOW}⚠️ Интерактивная настройка пропущена. Отредактируйте .env вручную.${NC}" "\n${YELLOW}⚠️ Interactive configuration skipped. Edit .env manually.${NC}"
        fi
    fi
}
