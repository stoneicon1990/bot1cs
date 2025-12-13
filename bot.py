import os
import socket
import logging
from datetime import datetime
import collections.abc

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

# Отримуємо змінні середовища з Render.com
BOT_TOKEN = os.environ.get('BOT_TOKEN')
MIX_SERVER_IP = os.environ.get('MIX_SERVER_IP')
MIX_SERVER_PORT = int(os.environ.get('MIX_SERVER_PORT', 27015))

# Перевірка обов'язкових змінних
if not BOT_TOKEN:
    logger.error("❌ Змінна BOT_TOKEN не встановлена")
    exit(1)

if not MIX_SERVER_IP:
    logger.error("❌ Змінна MIX_SERVER_IP не встановлена")
    exit(1)

def escape_markdown(text):
    """Екранує спецсимволи MarkdownV2"""
    if not text:
        return ""
    # Символи, які потрібно екранувати в MarkdownV2
    escape_chars = r'_*[]()~>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in str(text)])

def escape_for_markdown(text):
    """Екранує текст для MarkdownV2, включаючи крапки"""
    if not text:
        return ""
    # Екрануємо всі спецсимволи MarkdownV2
    escape_chars = r'_*[]()~>#+-=|{}.!'
    result = ''
    for char in str(text):
        if char in escape_chars:
            result += '\\' + char
        else:
            result += char
    return result

def get_server_info():
    """
    Отримує інформацію про сервер CS 1.6 через A2S запит
    """
    try:
        logger.info(f"🔍 Запит до сервера CS 1.6 {MIX_SERVER_IP}:{MIX_SERVER_PORT}")
        
        # Для CS 1.6 використовуємо протокол GoldSource
        with valve.source.a2s.ServerQuerier((MIX_SERVER_IP, MIX_SERVER_PORT), timeout=5.0) as server:
            info = server.info()
            
            # Спробуємо отримати список гравців
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
                'player_count': info['player_count'],
                'max_players': info['max_players'],
                'players_list': players_list,
                'game': info['game'],
                'folder': info['folder']
            }
            
    except valve.source.NoResponseError:
        logger.warning(f"⚠️ Сервер CS 1.6 {MIX_SERVER_IP}:{MIX_SERVER_PORT} не відповідає")
        return {
            'status': 'offline',
            'message': 'Сервер не відповідає на запит'
        }
    except socket.timeout:
        logger.warning(f"⚠️ Таймаут підключення до {MIX_SERVER_IP}:{MIX_SERVER_PORT}")
        return {
            'status': 'offline',
            'message': 'Таймаут підключення'
        }
    except socket.gaierror as e:
        logger.error(f"❌ Помилка DNS для {MIX_SERVER_IP}:{MIX_SERVER_PORT}: {e}")
return {
            'status': 'error',
            'message': f'Помилка DNS: {str(e)}'
        }
    except Exception as e:

        logger.error(f"❌ Помилка запиту до сервера CS 1.6: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

def check_server_availability():
    """Перевіряє доступність сервера CS 1.6"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((MIX_SERVER_IP, MIX_SERVER_PORT))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"❌ Помилка перевірки сервера CS 1.6: {e}")
        return False

async def mix_command(update: Update, context: CallbackContext):
    """Обробник команди /mix - показує інформацію про CS 1.6 MIX сервер"""
    try:
        logger.info(f"📱 Команда /mix від {update.effective_user.id}")
        
        # Відправляємо повідомлення про завантаження
        loading_msg = await update.message.reply_text("🔄 Отримую інформацію з сервера...")
        
        # Отримуємо інформацію про сервер
        data = get_server_info()
        
        if data['status'] == 'offline':
            await loading_msg.edit_text(
                f"🔴 Bot1cs Automix | [5x5] ({MIX_SERVER_IP}:{MIX_SERVER_PORT}) не відповідає.\n"
                f"Можливо, він вимкнений або недоступний."
            )
            return
            
        if data['status'] == 'error':
            await loading_msg.edit_text(
                f"⚠️ Помилка сервера CS 1.6 MIX: {data['message']}\n"
                f"Адреса: {MIX_SERVER_IP}:{MIX_SERVER_PORT}"
            )
            return

        # Отримуємо поточний час
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Екрануємо всі текстові поля для MarkdownV2
        server_name = escape_for_markdown(data['server_name'])
        map_name = escape_for_markdown(data['map'])
        escaped_ip = escape_for_markdown(MIX_SERVER_IP)
        escaped_port = escape_for_markdown(str(MIX_SERVER_PORT))
        escaped_current_time = escape_for_markdown(current_time)

        # Формуємо повідомлення з правильним екрануванням
        message = (
            f"🎮 *{server_name}*\n"
            f"🗺 Мапа: {map_name}\n"
            f"👥 Гравців: {escape_for_markdown(data['players'])}\n"
            f"🔗 Адреса: {escaped_ip}\\:{escaped_port}\n"  # Екрануємо двокрапку
        )

        # Додаємо список гравців, якщо вони є
        if data['players_list']:
            message += "\n*Список гравців:*\n"
            
            # Сортуємо гравців за очками (за спаданням)
            sorted_players = sorted(data['players_list'], key=lambda x: x.get('score', 0), reverse=True)
            
            for player in sorted_players:
                # Конвертуємо час гравця в хвилини:секунди
                minutes = int(player.get('duration', 0) // 60)
                seconds = int(player.get('duration', 0) % 60)
                player_time = f"{minutes:02d}:{seconds:02d}"
                
                # Екрануємо спецсимволи в імені гравця
                player_name = escape_for_markdown(player['name'])
                
                # Форматуємо рядок гравця
                message += (
                    f"• {player_name}: "
                    f"⏱ {player_time} \\| "  # Екрануємо вертикальну риску
                    f"🏆 {player.get('score', 0)} фрг\n"
                )
        else:
            message += "\n👤 *На сервері немає гравців*"

        # Додаємо час оновлення
        message += f"\n\n🕒 *Оновлено:* {escaped_current_time}"

        # Оновлюємо повідомлення замість завантаження
        await loading_msg.edit_text(
            message,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка в команді /mix: {e}")
        try:
            await update.message.reply_text(f"🚨 Помилка: {str(e)}")
        except:
            pass
async def start_command(update: Update, context: CallbackContext):
    """Обробник команди /start"""
    await update.message.reply_text(
        "🤖 Привіт! Я бот для відстеження сервера Bot1cs Automix | [5x5]\n\n"
        "Доступні команди:\n"
        "/mix - інформація про онлайн\n\n"
        f"📍 Сервер: {MIX_SERVER_IP}:{MIX_SERVER_PORT}"
    )

async def help_command(update: Update, context: CallbackContext):
    """Обробник команди /help"""
    await update.message.reply_text(
        "📖 *Доступні команди:*\n\n"
        "/mix - отримати інформацію про сервер CS 1\\.6 MIX\n"
        "/start - початок роботи з ботом\n"
        "/help - довідка\n\n"
        f"📍 Адреса сервера: {MIX_SERVER_IP}\\:{MIX_SERVER_PORT}",
        parse_mode='MarkdownV2'
    )

def run_bot():
    """Запускає Telegram бота"""
    # Створюємо додаток
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("mix", mix_command))
    application.add_handler(CommandHandler("help", help_command))

    # Запускаємо бота
    logger.info(f"🤖 Бот для CS 1.6 запущений!")
    logger.info(f"📡 Сервер: {MIX_SERVER_IP}:{MIX_SERVER_PORT}")
    application.run_polling()

if __name__ == "__main__":
    logger.info("🚀 Запуск бота для CS 1.6 MIX сервера...")
    
    # Перевіряємо з'єднання з сервером
    logger.info(f"🔍 Перевірка сервера CS 1.6 {MIX_SERVER_IP}:{MIX_SERVER_PORT}")
    if check_server_availability():
        logger.info("✅ Bot1cs Automix | [5x5] доступний")
    else:
        logger.warning("⚠️ Сервер CS 1.6 недоступний, але бот запускається...")
    
    # Запускаємо бота
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("👋 Бот зупинено")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")


