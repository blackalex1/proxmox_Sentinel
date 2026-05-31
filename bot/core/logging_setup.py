import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Настраивает асинхронно-совместимое логирование с записью в консоль, общий лог и отдельный лог варнингов."""
    # bot/core/logging_setup.py -> bot/config/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.abspath(os.path.join(current_dir, '../config'))
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'bot.log')
    warnings_file = os.path.join(log_dir, 'warnings.log')

    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Общий ротируемый файловый хэндлер (макс 10 МБ на файл, храним до 5 бэкапов)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # 2. Выделенный ротируемый файловый хэндлер для ВАРНИНГОВ и АЛЕРТОВ (макс 50 МБ на файл)
    # Записывает логи уровней WARNING, ERROR и CRITICAL
    warnings_handler = RotatingFileHandler(
        warnings_file,
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=1,  # Храним 1 бэкап при переполнении (старые строки удаляются)
        encoding='utf-8'
    )
    warnings_handler.setFormatter(log_formatter)
    warnings_handler.setLevel(logging.WARNING)

    # 3. Консольный хэндлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Очищаем старые хэндлеры, чтобы избежать дублирования записей при перезапуске
    root_logger.handlers = []
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(warnings_handler)
    root_logger.addHandler(console_handler)

    # Настраиваем уровень логирования для библиотеки asyncssh на WARNING,
    # чтобы не забивать логи INFO-сообщениями о каждом сессионном канале SSH.
    logging.getLogger('asyncssh').setLevel(logging.WARNING)

    logging.info(f"[Logging] Инициализировано общее логирование: {log_file} (5x10MB)")
    logging.info(f"[Logging] Инициализирован выделенный лог предупреждений: {warnings_file} (max 50MB)")
