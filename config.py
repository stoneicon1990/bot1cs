import os

CONFIG = {
    'bot_token': '8586477554:AAHuRxOY6ZiapNZ0yfo82h4eCNdqE04QcMQ',
    'mix_server_ip': '91.211.118.97',  # наприклад: '123.45.67.89'
    'mix_server_port': 27038,  # порт вашого сервера MIX
}

# Перевірка обов'язкових змінних
required_vars = ['BOT_TOKEN', 'SERVER_IP', 'MIX_SERVER_IP']
for var in required_vars:
    if not os.environ.get(var):
        raise Exception(f"❌ Не встановлено змінну оточення: {var}")


