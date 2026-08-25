#!/usr/bin/env bash

# Sentinel-Core Engine Setup Module
fetch_sentinel_core() {
    print_lang "\n${YELLOW}[3.5/5] Проверка и загрузка ядра безопасности sentinel-core...${NC}" "\n${YELLOW}[3.5/5] Checking and downloading sentinel-core security engine...${NC}"
    
    local FETCH_SCRIPT="${SCRIPT_DIR}/fetch_core.sh"
    if [ -f "${FETCH_SCRIPT}" ]; then
        chmod +x "${FETCH_SCRIPT}"
        if bash "${FETCH_SCRIPT}"; then
            print_lang "${GREEN}✓ Ядро sentinel-core готово к работе.${NC}" "${GREEN}✓ sentinel-core engine is ready.${NC}"
        else
            print_lang "${YELLOW}⚠️ Предупреждение: Не удалось загрузить последнюю версию sentinel-core. Будет использована локальная версия/fallback.${NC}" "${YELLOW}⚠️ Warning: Failed to download latest sentinel-core. Local/fallback engine will be used.${NC}"
        fi
    else
        print_lang "${YELLOW}⚠️ Скрипт fetch_core.sh не найден по пути ${FETCH_SCRIPT}.${NC}" "${YELLOW}⚠️ fetch_core.sh script not found at ${FETCH_SCRIPT}.${NC}"
    fi
}
