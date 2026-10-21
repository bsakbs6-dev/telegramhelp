import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from config import settings
import database
from handlers import admin, common, ocr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: Bot):
    """Sets up the Telegram Left Menu Command List."""
    try:
        # Default menu for regular users
        await bot.set_my_commands([
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="mode", description="⚙️ Режим (1:1 или Конспект)"),
            BotCommand(command="help", description="📖 Справка и возможности"),
            BotCommand(command="clear", description="🗑 Очистить очередь фото"),
        ], scope=BotCommandScopeDefault())

        # Admin menu for Super Admin
        await bot.set_my_commands([
            BotCommand(command="start", description="🏠 Главное меню"),
            BotCommand(command="admin", description="👑 Панель администратора"),
            BotCommand(command="genkey", description="🔑 Создать ключ доступа"),
            BotCommand(command="mode", description="⚙️ Режим (1:1 или Конспект)"),
            BotCommand(command="help", description="📖 Справка и возможности"),
            BotCommand(command="clear", description="🗑 Очистить очередь фото"),
        ], scope=BotCommandScopeChat(chat_id=settings.ADMIN_ID))

        logger.info("Bot menu commands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not setup bot commands: {e}")

async def main():
    logger.info("Initializing database...")
    await database.init_db()
    logger.info("Database initialized.")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(ocr.router)

    logger.info("Starting bot polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands(bot)
        me = await bot.get_me()
        logger.info(f"Bot authorized as @{me.username} (ID: {me.id})")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
