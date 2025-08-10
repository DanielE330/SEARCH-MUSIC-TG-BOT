import os
import telebot
from telebot import types
from yandex_music import Client
import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='music_bot.log'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot('TOKEN_TG')
client = Client('TOKEN_YA.MUSIC')
client.init()

user_search_results = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🎵 Привет, меломана! 🎧\n"
        "Я - твой музыкальный гид. Просто напиши мне название песни или исполнителя, "
        "и я найду для тебя эту композицию!\n\n"
        "Примеры запросов:\n"
        "• 'The Weeknd Blinding Lights'\n"
        "• 'Кино Группа крови'\n"
        "• 'Queen Bohemian Rhapsody'"
    )
    bot.reply_to(message, welcome_text)
    logger.info(f"Новый пользователь: @{message.from_user.username}")

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    logger.info(f"Поиск от @{message.from_user.username}: '{message.text}'")
    
    try:
        search_result = client.search(message.text)
        
        if not search_result or not search_result.tracks:
            bot.reply_to(message, "🔍 Ничего не найдено. Попробуй другой запрос.")
            return

        
        user_search_results[message.chat.id] = search_result.tracks.results[:5]  

        
        markup = types.InlineKeyboardMarkup()
        for idx, track in enumerate(user_search_results[message.chat.id]):
            duration = str(datetime.timedelta(milliseconds=track.duration_ms))[2:7] if track.duration_ms else ""
            artists = ', '.join(artist.name for artist in track.artists)
            btn_text = f"{idx+1}. {track.title} - {artists} {duration}"
            
            markup.add(types.InlineKeyboardButton(
                text=btn_text,
                callback_data=f"track_{idx}"
            ))

        bot.send_message(
            message.chat.id,
            "🎧 Найденные треки:",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Ошибка поиска: {str(e)}")
        bot.reply_to(message, "⚠️ Произошла ошибка при поиске. Попробуй позже.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('track_'))
def send_audio(call):
    try:
        track_index = int(call.data.split('_')[1])
        tracks = user_search_results.get(call.message.chat.id)
        
        if not tracks or track_index >= len(tracks):
            bot.answer_callback_query(call.id, "❌ Трек больше не доступен")
            return

        track = tracks[track_index]
        artists = ', '.join(artist.name for artist in track.artists)
        
        
        bot.answer_callback_query(call.id, "⏳ Загружаю трек...")

        
        download_info = track.get_download_info(get_direct_links=True)
        if not download_info:
            bot.answer_callback_query(call.id, "🚫 Этот трек нельзя скачать")
            return
            
        
        best_quality = max(download_info, key=lambda x: x.bitrate_in_kbps)
        
        
        filename = f"temp_{call.message.chat.id}_{track.id}.mp3"
        track.download(filename, codec='mp3', bitrate_in_kbps=best_quality.bitrate_in_kbps)
        
        
        with open(filename, 'rb') as audio_file:
            bot.send_audio(
                chat_id=call.message.chat.id,
                audio=audio_file,
                title=track.title,
                performer=artists,
                duration=int(track.duration_ms/1000) if track.duration_ms else None
            )
        
        logger.info(f"Отправлен трек: {artists} - {track.title} для @{call.from_user.username}")

    except Exception as e:
            logger.error(f"Ошибка загрузки: {str(e)}")
            bot.answer_callback_query(call.id, f"⚠️ Ошибка: {str(e)}", show_alert=True)
    finally:
            
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)

    logger.info("Запуск музыкального бота...")
    try:
        bot.polling(none_stop=True, interval=1)
    except Exception as e:
        logger.error(f"Бот остановлен: {str(e)}")

        
bot.polling(none_stop=True)
