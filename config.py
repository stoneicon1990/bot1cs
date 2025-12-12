import os

CONFIG = {
    'bot_token': os.environ.get('BOT_TOKEN'),
    'server_ip': os.environ.get('SERVER_IP'),
    'server_port': int(os.environ.get('SERVER_PORT', 27015)),
    'mix_server_ip': os.environ.get('MIX_SERVER_IP'),
    'mix_server_port': int(os.environ.get('MIX_SERVER_PORT', 27020))
}

# Перевірка обов'язкових змінних
required_vars = ['BOT_TOKEN', 'SERVER_IP', 'MIX_SERVER_IP']
for var in required_vars:
    if not os.environ.get(var):
        raise Exception(f"❌ Не встановлено змінну оточення: {var}")
