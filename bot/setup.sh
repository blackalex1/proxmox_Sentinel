#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get the absolute path of the directory containing the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MODULES_DIR="${SCRIPT_DIR}/setup_modules"

# Source modular installation components
source "${MODULES_DIR}/common.sh"
source "${MODULES_DIR}/dependencies.sh"
source "${MODULES_DIR}/config_wizard.sh"
source "${MODULES_DIR}/service_setup.sh"

# Main setup execution flow
main() {
    # 1. Base checks and setup
    check_root
    show_welcome_banner
    setup_install_proxy
    
    # 2. System and kernel configuration
    install_system_deps
    configure_auditd
    
    # 3. Python environment
    setup_python_venv
    install_python_requirements
    
    # 4. Interactive Configuration Wizard
    run_config_wizard
    
    # 5. Systemd service setup & guest validation
    install_systemd_service
    start_service_and_verify
}

# Execute main function
main "$@"
