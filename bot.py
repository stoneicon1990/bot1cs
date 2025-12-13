import os
import socket
import logging
from datetime import datetime
import collections.abc
from flask import Flask

# Фікс для python-valve на Python 3.13
collections.Mapping = collections.abc.Mapping
collections.Sequence = collections.abc.Sequence
collections.Iterable = collections.abc.Iterable

import valve.source.a2s
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Отримуємо змінні середовища
BOT_TOKEN = os.environ.get('BOT_TOKEN')
MIX_SERVER_IP = os.environ.get('MIX_SERVER_IP')
MIX_SERVER_PORT = int(os.environ.get('MIX_SERVER_PORT', 27015))

# Перевірка обов'язкових змінних
if not BOT_TOKEN or BOT_TOKEN == 'ВАШ_ТЕЛЕГРАМ_БОТ_ТОКЕН':
    logger.error("❌ Змінна BOT_TOKEN не встановлена")
    exit(1)

if not MIX_SERVER_IP or MIX_SERVER_IP == 'IP_АДРЕСА_ВАШОГО_СЕРВЕРА_MIX':
    logger.error("❌ Змінна MIX_SERVER_IP не встановлена")
    exit(1)

# Створюємо Flask додаток
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "🤖 CS 1.6 MIX Bot is running"

@flask_app.route('/health')
def health():
    return "OK", 200

def escape_markdown_v2(text):
    """Екранує спецсимволи MarkdownV2"""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    result = ''
    for char in str(text):
        if char in escape_chars:
            result += '\\' + char
        else:
            result += char
    return result

def get_server_info():
    """Отримує інформацію про сервер CS 1.6"""
    try:
        logger.info(f"🔍 Запит до сервера CS 1.6 {MIX_SERVER_IP}:{MIX_SERVER_PORT}")
        
        with valve.source.a2s.ServerQuerier((MIX_SERVER_IP, MIX_SERVER_PORT), timeout=5.0) as server:
            info = server.info()
            
            players_list = []
            try:
                players = server.players()
                for player in players['players']:
                    if player['name'] and player['name'].strip():
                        players_list.append({
                            'name': player['name'],
                            'duration': player['duration'],
                            'score': player['score'] if 'score' in player else 0
                        })
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося отримати список гравців: {e}")
            
            return {
                'status': 'online',
                'server_name': info['server_name'],
                'map': info['map'],
                'players': f"{info['player_count']}/{info['max_players']}",
                'players_list': players_list,
            }
            
    except valve.source.NoResponseError:
        return {'status': 'offline', 'message': 'Сервер не відповідає'}
    except socket.timeout:
        return {'status': 'offline', 'message': 'Таймаут підключення'}
    except socket.gaierror as e:
        return {'status': 'error', 'message': f'Помилка DNS: {str(e)}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

async def mix_command(update: Update, context: CallbackContext):
    """Команда /mix"""
    try:
        logger.info(f"📱 Команда /mix від {update.effective_user.id}")
        
        loading_msg = await update.message.reply_text("🔄 Отримую інформацію з сервера...")
        
        data = get_server_info()
        
        if data['status'] == 'offline':
            await loading_msg.edit_text(
                f"🔴 Сервер CS 1.6 MIX ({MIX_SERVER_IP}:{MIX_SERVER_PORT}) не відповідає.\n"
                f"Можливо, він вимкнений або недоступний."
            )
            return
            
        if data['status'] == 'error':
            await loading_msg.edit_text(
                f"⚠️ Помилка сервера CS 1.6 MIX: {data['message']}\n"
                f"Адреса: {MIX_SERVER_IP}:{MIX_SERVER_PORT}"
            )
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        server_name = escape_markdown_v2(data['server_name'])
        map_name = escape_markdown_v2(data['map'])
        players_count = escape_markdown_v2(data['players'])
        escaped_ip = escape_markdown_v2(MIX_SERVER_IP)
        escaped_port = escape_markdown_v2(str(MIX_SERVER_PORT))
        escaped_current_time = escape_markdown_v2(current_time)

        message = (
            f"🎮 *{server_name}*\n"
            f"🗺 Мапа: {map_name}\n"
            f"👥 Гравців: {players_count}\n"
            f"🔗 Адреса: {escaped_ip}\\:{escaped_port}\n"
        )

        if data['players_list']:
            message += "\n*Список гравців:*\n"
            
            sorted_players = sorted(data['players_list'], key=lambda x: x.get('score', 0), reverse=True)
            
            for player in sorted_players:
                minutes = int(player.get('duration', 0) // 60)
                seconds = int(player.get('duration', 0) % 60)
                player_time = f"{minutes:02d}\\:{seconds:02d}"
                player_name = escape_markdown_v2(player['name'])
                
                message += (
                    f"• {player_name}: "
                    f"⏱ {player_time} \\| "
                    f"🏆 {player.get('score', 0)} фрг\n"
                )
        else:
            message += "\n👤 *На сервері немає гравців*"

        message += f"\n\n🕒 *Оновлено:* {escaped_current_time}"

        await loading_msg.edit_text(message, parse_mode='MarkdownV2')
        
    except Exception as e:
        logger.error(f"❌ Помилка в команді /mix: {e}")
        try:
            await update.message.reply_text(f"🚨 Помилка: {str(e)}")
        except:
            pass

async def start_command(update: Update, context: CallbackContext):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 Привіт! Я бот для відстеження сервера Bot1cs Automix | [5x5]\n\n"
        "Доступні команди:\n"
        "/mix - інформація про онлайн\n\n"
        f"📍 Сервер: {MIX_SERVER_IP}:{MIX_SERVER_PORT}\n"
    )

def run_flask():
    """Запускає Flask сервер"""
    import threading
    def start():
        flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=start, daemon=True)
    thread.start()
    logger.info("🌐 Flask сервер запущений на порті 5000")

def run_bot():
    """Запускає Telegram бота"""
    # Спочатку запускаємо Flask
    run_flask()
    
    # Створюємо додаток для бота
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("mix", mix_command))
    
    # Запускаємо бота
    logger.info(f"🤖 Бот для CS 1.6 запущений!")
    logger.info(f"📡 Сервер: {MIX_SERVER_IP}:{MIX_SERVER_PORT}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    logger.info("🚀 Запуск бота для CS 1.6 MIX сервера...")
    
    # Запускаємо все
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("👋 Бот зупинено")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
