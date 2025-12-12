import os

CONFIG = {
    'bot_token': 'ВАШ_ТЕЛЕГРАМ_БОТ_ТОКЕН',
    'mix_server_ip': 'IP_АДРЕСА_ВАШОГО_СЕРВЕРА_MIX',  # наприклад: '123.45.67.89'
    'mix_server_port': 27038,  # порт вашого сервера MIX
}

# Перевірка обов'язкових змінних
required_vars = ['BOT_TOKEN', 'SERVER_IP', 'MIX_SERVER_IP']
for var in required_vars:
    if not os.environ.get(var):
        raise Exception(f"❌ Не встановлено змінну оточення: {var}")

