from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from datetime import datetime
import time
import socket
from threading import Thread

# Імпорт ваших функцій
from config import CONFIG
from server_info import get_server_info  # припускаючи, що ця функція існує
from web_server import run_web_server  # припускаючи, що ця функція існує

def escape_markdown(text):
    """Екранує спецсимволи MarkdownV2"""
    if not text:
        return ""
    escape_chars = r'_*[]()~>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in str(text)])

def check_server_availability(ip, port, timeout=3):
    """Перевіряє доступність сервера"""
    try:
        socket.create_connection((ip, port), timeout=timeout)
        return True
    except (socket.gaierror, socket.timeout, ConnectionRefusedError) as e:
        return False

async def mix_command(update: Update, context: CallbackContext):
    """Обробник команди /mix - показує інформацію про MIX сервер"""
    try:
        # Отримуємо конфігурацію MIX сервера
        mix_ip = CONFIG.get('mix_server_ip')
        mix_port = CONFIG.get('mix_server_port', 27015)  # значення за замовчуванням
        
        # Перевіряємо, чи вказана конфігурація
        if not mix_ip or mix_ip == 'ваш_mix_сервер_ip':
            await update.message.reply_text(
                "⚠️ Сервер MIX не налаштований.\n"
                "Будь ласка, зверніться до адміністратора."
            )
            return
        
        # Перевіряємо доступність сервера
        if not check_server_availability(mix_ip, mix_port):
            await update.message.reply_text(
                f"🔴 Сервер MIX ({mix_ip}:{mix_port}) недоступний.\n"
                f"Перевірте правильність IP-адреси та порту."
            )
            return
        
        # Отримуємо інформацію про сервер
        data = get_server_info(mix_ip, mix_port)
        
        if data['status'] == 'offline':
            await update.message.reply_text("🔴 Сервер MIX не відповідає. Можливо, він вимкнений або недоступний.")
            return
        if data['status'] == 'error':
            await update.message.reply_text(f"⚠️ Помилка сервера MIX: {data['message']}")
            return

        # Отримуємо поточний час для відображення
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Формуємо повідомлення для /mix
        message = (
            f"🎮 *{escape_markdown(data['server_name'])} MIX*\n"
            f"🗺 Мапа: {escape_markdown(data['map'])}`\n"
            f"👥 *Список гравців:*\n"
        )

        # Додаємо інформацію про кожного гравця
        for player in data['players_list']:
            # Конвертуємо час гравця в хвилини:секунди
            player_time = time.strftime("%M:%S", time.gmtime(player.get('duration', 0)))
            # Екрануємо спецсимволи в імені гравця
            player_name = escape_markdown(player['name'])
            # Форматуємо рядок гравця
            message += (
                f"• {player_name}: "
                f"🕒 {player_time} \\| "
                f"{player.get('score', 0)} вбивств\n"
            )

        # Додаємо час останнього оновлення
        message += f"\n🕒 *Останнє оновлення:* {escape_markdown(current_time)}"

        # Відправляємо фото з описом
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=data['map_image'],
            caption=message,
            parse_mode='MarkdownV2'
        )
        
    except KeyError as e:
        await update.message.reply_text(f"🚨 Помилка формату даних: відсутнє поле {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"🚨 Помилка: {str(e)}")

def run_bot():
    """Запускає Telegram бота"""
    # Створюємо додаток за допомогою білдера
    application = ApplicationBuilder().token(CONFIG['bot_token']).build()

    # Додаємо обробник тільки для команди /mix
    application.add_handler(CommandHandler("mix", mix_command))
    # Запускаємо бота
    print("🤖 Бот запущений! Для зупинки натисніть Ctrl+C")
    print(f"📡 Використовується сервер MIX: {CONFIG.get('mix_server_ip')}:{CONFIG.get('mix_server_port', 27015)}")
    application.run_polling()

if name == "main":
    # Перевіряємо наявність токена бота
    if not CONFIG.get('bot_token') or CONFIG['bot_token'] == 'ваш_токен':
        print("❌ Помилка: Не вказано токен бота в конфігурації!")
        exit(1)
    
    # Перевіряємо наявність IP сервера MIX
    if not CONFIG.get('mix_server_ip') or CONFIG['mix_server_ip'] == 'ваш_mix_сервер_ip':
        print("❌ Помилка: Не вказано IP-адресу сервера MIX в конфігурації!")
        print("📝 Відредагуйте файл config.py та вкажіть правильний IP-адресу")
        exit(1)
    
    print("🧪 Тестування підключення до сервера CS...")
    
    # Запускаємо веб-сервер у окремому потоці
    web_thread = Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    print("🌐 Веб-сервер запущений у фоновому режимі")

    # Запускаємо бота в основному потоці
    run_bot()
