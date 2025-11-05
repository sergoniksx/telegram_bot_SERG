import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp
import requests
from io import BytesIO

load_dotenv()

# Используйте НОВЫЙ токен вместо старого
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8400809798:AAGMAX5ajxOamBFGaqWvAg7PFJ250SK04nA')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для скачивания видео из Instagram
def download_instagram_video(url):
    """
    Скачивает видео из Instagram по ссылке
    """
    try:
        # Используем API для скачивания
        api_url = f"https://www.instagram.com/oembed/?url={url}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Альтернативный способ через сторонний API
        download_url = f"https://instagram-video-downloader.p.rapidapi.com/"
        
        # Используем instagrapi для загрузки
        try:
            from instagrapi import Client
            
            cl = Client()
            # Получаем информацию о посте
            media = cl.media_info(url.split('/')[-2])
            
            if media.media_type == 1:  # Фото
                return {"type": "photo", "url": media.media_list[0].path}
            elif media.media_type == 2:  # Видео
                return {"type": "video", "url": media.video_url}
            elif media.media_type == 8:  # Карусель (фото/видео)
                media_list = []
                for item in media.media_list:
                    if item.media_type == 2:  # Видео в карусели
                        media_list.append({"type": "video", "url": item.video_url})
                    else:
                        media_list.append({"type": "photo", "url": item.path})
                return {"type": "carousel", "items": media_list}
        except:
            pass
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при скачивании: {e}")
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео из Instagram.\n\n"
        "📝 Просто отправь мне ссылку на видео Instagram и я его скачаю.\n\n"
        "Например:\n"
        "https://www.instagram.com/p/ABC123DEF456/\n\n"
        "или\n\n"
        "https://www.instagram.com/reel/ABC123DEF456/",
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🆘 <b>Справка:</b>\n\n"
        "1️⃣ Отправь ссылку на Instagram пост/видео/рилс\n"
        "2️⃣ Бот скачает видео\n"
        "3️⃣ Получишь файл в Telegram\n\n"
        "<b>Поддерживаемые ссылки:</b>\n"
        "• instagram.com/p/XXX (посты)\n"
        "• instagram.com/reel/XXX (рилсы)\n"
        "• instagram.com/stories/... (сторис)",
        parse_mode="HTML"
    )

@dp.message()
async def process_message(message: types.Message):
    """
    Обработка ссылок на Instagram
    """
    text = message.text
    
    # Проверяем, содержит ли сообщение ссылку на Instagram
    if "instagram.com" not in text and not text.startswith("http"):
        await message.answer("❌ Это не ссылка на Instagram.\n\nОтправь ссылку вида: https://www.instagram.com/...")
        return
    
    # Показываем статус загрузки
    status_message = await message.answer("⏳ Загружаю видео...")
    
    try:
        # Скачиваем видео
        result = download_instagram_video(text)
        
        if result is None:
            await status_message.edit_text(
                "❌ Не удалось скачать видео.\n\n"
                "Возможные причины:\n"
                "• Неверная ссылка\n"
                "• Видео удалено или недоступно\n"
                "• Аккаунт приватный"
            )
            return
        
        if result["type"] == "video":
            # Отправляем видео
            try:
                response = requests.get(result["url"], timeout=30)
                video_file = BytesIO(response.content)
                video_file.name = "instagram_video.mp4"
                
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=types.FSInputFile(video_file),
                    caption="✅ Видео из Instagram"
                )
                await status_message.delete()
                
            except Exception as e:
                logger.error(f"Ошибка при отправке видео: {e}")
                await status_message.edit_text(f"❌ Ошибка при отправке: {str(e)}")
        
        elif result["type"] == "photo":
            response = requests.get(result["url"], timeout=30)
            photo_file = BytesIO(response.content)
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=types.FSInputFile(photo_file),
                caption="✅ Фото из Instagram"
            )
            await status_message.delete()
        
        elif result["type"] == "carousel":
            # Отправляем группу медиа
            media_group = types.MediaGroupPhoto() if all(
                item["type"] == "photo" for item in result["items"]
            ) else types.MediaGroupVideo()
            
            for item in result["items"]:
                response = requests.get(item["url"], timeout=30)
                if item["type"] == "photo":
                    media_group.attach_photo(types.FSInputFile(BytesIO(response.content)))
                else:
                    media_group.attach_video(types.FSInputFile(BytesIO(response.content)))
            
            await bot.send_media_group(chat_id=message.chat.id, media=media_group)
            await status_message.delete()
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_message.edit_text(f"❌ Произошла ошибка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
