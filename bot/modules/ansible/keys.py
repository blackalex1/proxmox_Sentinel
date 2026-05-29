import os
import logging

def check_and_generate_ansible_keys(directory: str) -> tuple:
    """Проверяет наличие приватного ключа Ansible, при отсутствии генерирует новую ED25519 пару."""
    priv_path = os.path.join(directory, 'id_ed25519_ansible')
    pub_path = priv_path + '.pub'
    
    if os.path.exists(priv_path) and os.path.exists(pub_path):
        return True, False # Ключи уже существовали
        
    try:
        import asyncssh
        key = asyncssh.generate_private_key('ssh-ed25519')
        priv_bytes = key.export_private_key()
        pub_bytes = key.export_public_key()
        
        # Убедимся, что папка существует
        os.makedirs(directory, exist_ok=True)
        
        with open(priv_path, 'wb') as f:
            f.write(priv_bytes)
        with open(pub_path, 'wb') as f:
            f.write(pub_bytes)
            
        if os.name != 'nt':
            try:
                os.chmod(priv_path, 0o600)
                os.chmod(pub_path, 0o644)
            except Exception:
                pass
                
        logging.info(f"Успешно сгенерирована новая пара ED25519 ключей для Ansible в {directory}")
        return True, True # Ключи были сгенерированы впервые
    except Exception as e:
        logging.error(f"Ошибка генерации SSH ключей для Ansible: {e}")
        return False, False
