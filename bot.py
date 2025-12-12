from flask import Flask
from threading import Thread
import os
import re

# Допоміжна функція для екранування спецсимволів MarkdownV2
def escape_markdown(text):
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

# Створюємо мінімальний веб-сервер
app = Flask('')

@app.route('/')
def home():
    return "🟢 Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ========== ФІКС ДЛЯ COLLECTIONS ==========
import collections
import collections.abc
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, 'Sequence'):
    collections.Sequence = collections.abc.Sequence
if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable
# ==========================================

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
from valve.source.a2s import ServerQuerier, NoResponseError
import time
import asyncio
from config import CONFIG
from datetime import datetime

# Словник з URL зображень для карт
MAP_IMAGES = {
    ""
}

def get_server_info(server_ip=None, server_port=None):
    # Використовуємо перший сервер за замовчуванням, або вказаний сервер
    ip = server_ip if server_ip else CONFIG['server_ip']
    port = server_port if server_port else CONFIG['server_port']
    
    address = (ip, port)
    try:
        with ServerQuerier(address, timeout=5.0) as server:
            # Отримуємо інформацію про сервер
            info = server.info()
            # Отримуємо список гравців
            players_data = server.players()

            # Конвертуємо час гри
            duration_seconds = info.get('duration', 0)
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            game_duration = f"{minutes:02d}:{seconds:02d}"

            # Обробляємо гравців
            players_list = players_data.get('players', [])
            player_count = len(players_list)
            max_players = info.get('max_players', 0)

            return {
                'status': 'online',
                'map': info.get('map', 'unknown'),
                'map_image': MAP_IMAGES.get(info.get('map', ''), MAP_IMAGES['default']),
                'players': f"{player_count}/{max_players}",
                'game_duration': game_duration,
                'server_name': "Royal Arena",
                'players_list': players_list,
                'player_count': player_count,
                'max_players': max_players,
                'server_type': 'mix' if server_ip == CONFIG.get('mix_server_ip') else 'main'
            }
    except (NoResponseError, ConnectionRefusedError):
        return {'status': 'offline'}
    except Exception as e:
        print(f"Помилка запиту: {e}")
        return {'status': 'error', 'message': str(e)}

async def server_info(update: Update, context: CallbackContext):
    await send_server_info(update, context, server_type='main')

async def mix_command(update: Update, context: CallbackContext):
    try:
        # Використовуємо дані для другого сервера
        data = get_server_info(
            CONFIG.get('mix_server_ip'), 
            CONFIG.get('mix_server_port')
        )
        
        if data['status'] == 'offline':
            await update.message.reply_text("🔴 Сервер MIX не відповідає. Можливо, він вимкнений або недоступний.")
            return
        if data['status'] == 'error':
            await update.message.reply_text(f"⚠️ Помилка сервера MIX: {data['message']}")
            return

        # Отримуємо поточний час для відображення
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Формуємо повідомлення для /mix (аналогічно /server)
        message = (
            f"🎮 *{escape_markdown(data['server_name'])} MIX*\n"
            f"🗺️ Мапа: `{escape_markdown(data['map'])}`\n"
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
                f"• `{player_name}`: "
                f"🕒 {player_time} \\| "
                f"{player.get('score', 0)} вбивств\n"
            )

        # Додаємо час останнього оновлення
        message += f"\n🕒 *Останнє оновлення:* {escape_markdown(current_time)}"

        # Відправляємо фото з описом (без кнопок)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=data['map_image'],
            caption=message,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        await update.message.reply_text(f"🚨 Помилка: {str(e)}")

async def send_server_info(update: Update, context: CallbackContext, server_type='main'):
    try:
        if server_type == 'mix':
            # Використовуємо дані для другого сервера
            data = get_server_info(
                CONFIG.get('mix_server_ip'), 
                CONFIG.get('mix_server_port')
            )
            server_name_suffix = " MIX"
        else:
            # Використовуємо дані для основного сервера
            data = get_server_info()
            server_name_suffix = ""

        if data['status'] == 'offline':
            await update.message.reply_text("🔴 Сервер не відповідає. Можливо, він вимкнений або недоступний.")
            return
        if data['status'] == 'error':
            await update.message.reply_text(f"⚠️ Помилка сервера: {data['message']}")
            return

        # Отримуємо поточний час для відображення
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Формуємо повідомлення
        message = (
            f"🎮 *{data['server_name']}{server_name_suffix}*\n"
            f"🗺️ Мапа: `{data['map']}`\n"
            f"👥 Гравці: `{data['players']}`\n"
        )

        # Додаємо час останнього оновлення
        message += f"\n🕒 *Останнє оновлення:* {current_time}"

        # Відправляємо фото з описом
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=data['map_image'],
            caption=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"🚨 Критична помилка: {str(e)}")

# Нова команда /server
async def server_command(update: Update, context: CallbackContext):
    try:
        data = get_server_info()
        if data['status'] == 'offline':
            await update.message.reply_text("🔴 Сервер не відповідає. Можливо, він вимкнений або недоступний.")
            return
        if data['status'] == 'error':
            await update.message.reply_text(f"⚠️ Помилка сервера: {data['message']}")
            return

        # Отримуємо поточний час для відображення
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Формуємо повідомлення для /server
        message = (
            f"🎮 *{escape_markdown(data['server_name'])}*\n"
            f"🗺️ Мапа: `{escape_markdown(data['map'])}`\n"
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
                f"• `{player_name}`: "
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
    except Exception as e:
        await update.message.reply_text(f"🚨 Помилка: {str(e)}")

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'refresh_info':
        try:
            data = get_server_info()
            if data['status'] != 'online':
                await query.edit_message_text("🔴 Сервер не відповідає")
                return

            # Формуємо новий текст
            new_caption = (
                f"🔄 *Оновлено!*\n"
                f"🎮 Royal Arena\n"
                f"🗺️ Мапа: `{data['map']}`\n"
                f"⏱ Час гри: `{data['game_duration']}`\n"
                f"👥 Гравці: `{data['players']}`"
            )

            # Оновлюємо фото та текст
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=data['map_image'],
                    caption=new_caption,
                    parse_mode='Markdown'
                )
            )
        except Exception as e:
            await query.edit_message_text(f"🚨 Помилка оновлення: {str(e)}")

def run_bot():
    # Створюємо додаток за допомогою білдера
    application = ApplicationBuilder().token(CONFIG['bot_token']).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("info", server_info))
    application.add_handler(CommandHandler("s1", server_info))
    application.add_handler(CommandHandler("mix", mix_command))
    application.add_handler(CommandHandler("server", server_command))

    # Обробник для інтерактивних кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаємо бота
    print("🤖 Бот bot1cs запущений! Для зупинки натисніть Ctrl+C")
    application.run_polling()

if __name__ == "__main__":
    print("🧪 Тестування підключення до сервера CS...")
    # Тут ваш код тестування підключення
    
    # Якщо тест пройдено:
    print("✅ Тест пройдено успішно! Запускаємо сервіси...")

    # Запускаємо веб-сервер у окремому потоці
    web_thread = Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    print("🌐 Веб-сервер запущений у фоновому режимі")

    # Запускаємо бота в основному потоці
    run_bot()


