from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from config import settings
import database
from keyboards import get_unauthorized_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args

    # Check if a referral / invite key was passed via deep link: /start KEY-XXXXX
    if args and args.strip().startswith("KEY-"):
        is_ok, msg = await database.redeem_invite_key(
            key=args.strip(),
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        if is_ok:
            await message.answer(
                f"🎉 {msg}\n\n"
                "Добро пожаловать в бота оцифровки лекций!\n"
                "📸 Просто отправьте фотографии конспекта (по одной или альбомом).\n"
                "Бот соберет их, распознает текст, определит структуру и предложит сохранить в PDF или текстовом виде."
            )
            return
        else:
            await message.answer(msg)

    # Check authorization
    authorized = await database.is_user_authorized(user_id)
    if not authorized:
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "🔒 Этот бот работает по системе приглашений. Для доступа вам нужен персональный ключ.\n\n"
            "Отправьте ваш ключ доступа прямо в чат или используйте команду:\n"
            "<code>/register ВАШ_КЛЮЧ</code>\n\n"
            "<i>(Если у вас нет ключа, обратитесь к администратору бота)</i>",
            parse_mode="HTML",
            reply_markup=get_unauthorized_keyboard()
        )
        return

    # Authorized user
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "📚 <b>Я — умный ассистент по оцифровке лекций и конспектов.</b>\n\n"
        "⚡ <b>Как это работает:</b>\n"
        "1. Отправьте мне фотографии ваших конспектов (можно сразу пачкой или по одной).\n"
        "2. Бот покажет, сколько страниц получено, и спросит, готовы ли вы начать.\n"
        "3. ИИ найдет начало и конец лекции, исправит опечатки и структурирует материал.\n"
        "4. Вы сможете получить результат в красивом <b>PDF файле</b> или сообщением в чат!\n\n"
        "📷 Жду ваших фотографий!",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "enter_key_prompt")
async def cb_enter_key_prompt(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔑 Пожалуйста, введите ваш ключ доступа в формате:\n<code>KEY-XXXXXXXXXX</code>",
        parse_mode="HTML"
    )

@router.message(Command("register"))
async def cmd_register(message: Message, command: CommandObject):
    key = command.args
    if not key:
        await message.answer(
            "ℹ️ Укажите ключ после команды:\n<code>/register KEY-XXXXXXXXXX</code>",
            parse_mode="HTML"
        )
        return

    is_ok, res_text = await database.redeem_invite_key(
        key=key.strip(),
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    if is_ok:
        await message.answer(
            f"{res_text}\n\n"
            "Теперь вы можете присылать фотографии лекций для распознавания!"
        )
    else:
        await message.answer(res_text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Справка по боту</b>\n\n"
        "• Отправьте одно или несколько фото конспекта.\n"
        "• Бот буферизует их и предложит нажать <b>«Распознать»</b>.\n"
        "• Выберите формат: <b>PDF</b>, <b>текст</b> или <b>оба сразу</b>.\n"
        "• Бот сам определит структуру темы, выделит определения и формулы.\n\n"
        "Администраторские команды: /admin, /genkey (только для админа).",
        parse_mode="HTML"
    )
