import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import aiohttp
import re

load_dotenv()

BOT_TOKEN = os.getenv('8400809798:AAFQL1uvASYB8MzGv4U1wJLPmesu-rkHuvU')
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Кэш для скачанных видео (чтобы не скачивать дважды)
video_cache = {}

async def get_instagram_video(url: str):
    """
    Скачивает видео из Instagram через API
    """
    try:
        # Очищаем URL
        url = url.strip()
        
        # Проверяем формат ссылки
        if not re.match(r'https?://(www\.)?instagram\.com', url):
            return None, "❌ Неверный формат ссылки Instagram"
        
        # Используем instagrapi для получения информации
        try:
            from instagrapi import Client
            
            client = Client()
            
            # Получаем ID медиа из ссылки
            media_id = url.split('/')[-2]
            
            try:
                # Пытаемся получить информацию о медиа
                media = client.media_info(media_id)
                
                if media.media_type == 1:  # Фото
                    return {
                        "type": "photo",
                        "url": media.media_list[0].path,
                        "caption": media.caption_text or "Фото из Instagram"
                    }, None
                
                elif media.media_type == 2:  # Видео
                    return {
                        "type": "video",
                        "url": media.video_url,
                        "thumbnail": media.thumbnail_url,
                        "caption": media.caption_text or "Видео из Instagram"
                    }, None
                
                elif media.media_type == 8:  # Карусель
                    items = []
                    for idx, item in enumerate(media.media_list):
                        if item.media_type == 2:  # Видео
                            items.append({
                                "type": "video",
                                "url": item.video_url,
                                "index": idx + 1
                            })
                        else:  # Фото
                            items.append({
                                "type": "photo",
                                "url": item.path,
                                "index": idx + 1
                            })
                    
                    return {
                        "type": "carousel",
                        "items": items,
                        "caption": media.caption_text or "Карусель из Instagram"
                    }, None
            
            except Exception as e:
                logger.error(f"Ошибка instagrapi: {e}")
                return None, f"❌ Не удалось получить информацию: {str(e)}"
        
        except ImportError:
            logger.warning("instagrapi не установлен, используем альтернативный метод")
            
            # Альтернативный способ через API
            async with aiohttp.ClientSession() as session:
                try:
                    # Используем публичный API для получения ссылки на видео
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    async with session.get(url + "?__a=1&__w=1", headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data, None
                except:
                    pass
            
            return None, "❌ Не удалось скачать видео. Попробуйте позже."
    
    except Exception as e:
        logger.error(f"Ошибка при скачивании: {e}")
        return None, f"❌ Ошибка: {str(e)}"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Я бот для скачивания видео из Instagram.\n\n"
        "📝 <b>Что делать:</b>\n"
        "1️⃣ Отправь мне ссылку на видео Instagram\n"
        "2️⃣ Жди загрузки\n"
        "3️⃣ Получи видео в Telegram\n\n"
        "📌 <b>Поддерживаемые ссылки:</b>\n"
        "• Posts: instagram.com/p/XXX\n"
        "• Reels: instagram.com/reel/XXX\n"
        "• Stories: instagram.com/stories/...\n\n"
        "/help - справка\n"
        "/about - о боте",
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда /help"""
    await message.answer(
        "🆘 <b>Справка:</b>\n\n"
        "<b>Как использовать:</b>\n"
        "1. Найди видео в Instagram\n"
        "2. Скопируй ссылку (нажми на три точки → Копировать ссылку)\n"
        "3. Отправь ссылку мне\n"
        "4. Жди, пока я скачаю видео\n\n"
        "<b>Примеры ссылок:</b>\n"
        "<code>https://www.instagram.com/p/ABC123/</code>\n"
        "<code>https://www.instagram.com/reel/ABC123/</code>\n\n"
        "❓ Вопросы? Напишите /about",
        parse_mode="HTML"
    )

@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    """Команда /about"""
    await message.answer(
        "ℹ️ <b>О боте:</b>\n\n"
        "Instagram Video Downloader Bot v1.0\n\n"
        "✨ Возможности:\n"
        "• Скачивание видео с Instagram\n"
        "• Скачивание фото\n"
        "• Поддержка каруселей\n"
        "• Быстрая работа\n\n"
        "🔒 Ваша приватность в безопасности!\n"
        "Я не сохраняю личные данные.\n\n"
        "📧 По вопросам: отправьте /help",
        parse_mode="HTML"
    )

@dp.message()
async def process_message(message: types.Message):
    """Обработка сообщений с ссылками"""
    text = message.text
    
    # Проверяем, содержит ли сообщение ссылку на Instagram
    if not text or "instagram.com" not in text:
        await message.answer(
            "❌ Это не ссылка на Instagram.\n\n"
            "Отправь ссылку вида:\n"
            "<code>https://www.instagram.com/p/...</code>\n\n"
            "/help - справка",
            parse_mode="HTML"
        )
        return
    
    # Показываем статус загрузки
    status_msg = await message.answer("⏳ Загружаю видео из Instagram...")
    
    try:
        # Скачиваем видео
        result, error = await get_instagram_video(text)
        
        if error:
            await status_msg.edit_text(error)
            return
        
        if result is None:
            await status_msg.edit_text(
                "❌ Не удалось скачать видео.\n\n"
                "<b>Возможные причины:</b>\n"
                "• Неверная ссылка\n"
                "• Видео удалено или недоступно\n"
                "• Аккаунт приватный\n"
                "• Истекла сессия\n\n"
                "/help - справка",
                parse_mode="HTML"
            )
            return
        
        # Отправляем результат
        if result["type"] == "video":
            await status_msg.edit_text("📥 Загружаю в Telegram...")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(result["url"]) as resp:
                        video_data = await resp.read()
                
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=types.BufferedInputFile(
                        file=video_data,
                        filename="instagram_video.mp4"
                    ),
                    caption=f"✅ {result['caption']}",
                    parse_mode="HTML"
                )
                await status_msg.delete()
                
            except Exception as e:
                logger.error(f"Ошибка отправки видео: {e}")
                await status_msg.edit_text(
                    f"❌ Ошибка при отправке видео\n\n"
                    f"Попробуйте позже или отправьте другую ссылку.",
                    parse_mode="HTML"
                )
        
        elif result["type"] == "photo":
            async with aiohttp.ClientSession() as session:
                async with session.get(result["url"]) as resp:
                    photo_data = await resp.read()
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=types.BufferedInputFile(
                    file=photo_data,
                    filename="instagram_photo.jpg"
                ),
                caption=f"✅ {result['caption']}",
                parse_mode="HTML"
            )
            await status_msg.delete()
        
        elif result["type"] == "carousel":
            await status_msg.edit_text(f"📥 Загружаю {len(result['items'])} файлов...")
            
            media_group = []
            for idx, item in enumerate(result["items"]):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(item["url"]) as resp:
                            file_data = await resp.read()
                    
                    if item["type"] == "video":
                        media = types.InputMediaVideo(
                            media=types.BufferedInputFile(
                                file=file_data,
                                filename=f"video_{idx}.mp4"
                            ),
                            caption="✅ Видео" if idx == 0 else None
                        )
                    else:
                        media = types.InputMediaPhoto(
                            media=types.BufferedInputFile(
                                file=file_data,
                                filename=f"photo_{idx}.jpg"
                            ),
                            caption="✅ Фото" if idx == 0 else None
                        )
                    
                    media_group.append(media)
                
                except Exception as e:
                    logger.error(f"Ошибка загрузки файла {idx}: {e}")
            
            if media_group:
                await bot.send_media_group(
                    chat_id=message.chat.id,
                    media=media_group
                )
                await status_msg.delete()
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка: {str(e)}")

async def main():
    """Запуск бота"""
    logger.info("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
