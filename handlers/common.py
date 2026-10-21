import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from config import settings
import database
from keyboards import (
    get_unauthorized_keyboard,
    get_main_reply_keyboard,
    get_mode_choice_keyboard
)

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID

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
            user_mode = await database.get_user_mode(user_id)
            await message.answer(
                f"🎉 {msg}\n\n"
                "Добро пожаловать в бота оцифровки лекций!\n"
                "📸 Просто отправьте фотографии конспекта (по одной или альбомом).\n"
                "Бот соберет их, распознает текст и предложит сохранить в PDF или сообщением в чат.",
                reply_markup=get_main_reply_keyboard(is_admin=is_admin(user_id), mode=user_mode)
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
    user_mode = await database.get_user_mode(user_id)
    mode_desc = "🧠 <b>Структурированный конспект</b> (выделение главного, формул, без изменения порядка слов)" if user_mode == "structured" else "🎯 <b>Дословно 1:1</b> (символ в символ как в оригинале)"

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "📚 <b>Я — умный ассистент по оцифровке лекций и конспектов.</b>\n\n"
        f"⚙️ <b>Текущий режим:</b> {mode_desc}\n\n"
        "⚡ <b>Как это работает:</b>\n"
        "1. Отправьте мне фотографии ваших конспектов (можно сразу пачкой или по одной).\n"
        "2. Бот покажет, сколько страниц получено, и предложит начать распознавание.\n"
        "3. Выберите формат: <b>PDF</b> или <b>текстом в чат</b>.\n\n"
        "📷 Жду ваших фотографий!",
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin(user_id), mode=user_mode)
    )

@router.message(Command("mode"))
@router.message(F.text.startswith("⚙️ Режим:"))
async def cmd_mode(message: Message):
    user_id = message.from_user.id
    if not await database.is_user_authorized(user_id):
        return
    current_mode = await database.get_user_mode(user_id)
    text = (
        "⚙️ <b>Выберите режим распознавания:</b>\n\n"
        "🧠 <b>Структурированный конспект</b> — бот находит начало и конец лекции, выделяет темы, "
        "определения и формулы жирным шрифтом, <b>строго сохраняя авторский порядок предложений</b>.\n\n"
        "🎯 <b>Дословно 1:1</b> — точный перевод символ в символ, без каких-либо изменений, "
        "сокращений или форматирования."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_mode_choice_keyboard(current_mode))

@router.callback_query(F.data.in_(["set_mode_structured", "set_mode_exact"]))
async def cb_set_mode(callback: CallbackQuery):
    user_id = callback.from_user.id
    new_mode = "structured" if callback.data == "set_mode_structured" else "exact"
    await database.set_user_mode(user_id, new_mode)

    mode_name = "🧠 Структурированный конспект" if new_mode == "structured" else "🎯 Дословно 1:1"
    await callback.message.edit_text(
        f"✅ <b>Режим успешно переключен на:</b>\n{mode_name}\n\n"
        "Все последующие фотографии будут обрабатываться в этом режиме.",
        parse_mode="HTML"
    )
    await callback.answer(f"Режим: {mode_name}")

    # Update bottom menu
    await callback.message.answer(
        "Панель обновлена 👇",
        reply_markup=get_main_reply_keyboard(is_admin=is_admin(user_id), mode=new_mode)
    )

@router.callback_query(F.data == "close_mode_menu")
async def cb_close_mode_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

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
        user_mode = await database.get_user_mode(message.from_user.id)
        await message.answer(
            f"{res_text}\n\n"
            "Теперь вы можете присылать фотографии лекций для распознавания!",
            reply_markup=get_main_reply_keyboard(is_admin=is_admin(message.from_user.id), mode=user_mode)
        )
    else:
        await message.answer(res_text)

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Справка и возможности бота</b>\n\n"
        "• <b>Загрузка:</b> отправьте одно или сразу несколько фото конспекта (альбомом).\n"
        "• <b>Режимы:</b>\n"
        "  1. 🧠 <i>Структурированный</i> — находит начало/конец лекции, темы, формулы, не меняя порядок слов.\n"
        "  2. 🎯 <i>Дословно 1:1</i> — точный символ в символ перевод без изменений.\n"
        "• <b>Форматы:</b> PDF-файл, текст в чат или оба сразу.\n\n"
        "Команды быстрого доступа всегда доступны в меню слева от поля ввода!",
        parse_mode="HTML"
    )

@router.message(F.text == "📸 Отправить конспект")
async def msg_send_photos_hint(message: Message):
    await message.answer("📸 Прикрепите и отправьте фотографии ваших конспектов сюда в чат!")
