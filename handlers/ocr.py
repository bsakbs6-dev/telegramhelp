import os
import html
import asyncio
import logging
from typing import Dict, List
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from config import settings
import database
from keyboards import (
    get_batch_control_keyboard,
    get_format_choice_keyboard,
    get_unauthorized_keyboard,
    get_mode_choice_keyboard
)
from services.ocr_service import ocr_service
from services.pdf_service import pdf_service

logger = logging.getLogger(__name__)
router = Router()

class UserBatch:
    def __init__(self):
        self.photos: List[str] = []
        self.control_msg_id: int | None = None
        self.debounce_task: asyncio.Task | None = None
        self.is_processing: bool = False

user_batches: Dict[int, UserBatch] = {}

def get_or_create_batch(user_id: int) -> UserBatch:
    if user_id not in user_batches:
        user_batches[user_id] = UserBatch()
    return user_batches[user_id]

async def debounce_notify_user(user_id: int, chat_id: int, bot: Bot):
    """
    Waits 1.2 seconds for any remaining photos in an album/burst,
    then updates or sends the interactive batch prompt.
    """
    await asyncio.sleep(1.2)
    batch = get_or_create_batch(user_id)
    if not batch.photos:
        return

    count = len(batch.photos)
    current_mode = await database.get_user_mode(user_id)
    mode_title = "🧠 <b>Структурированный конспект</b> (выделение главного, без изменения порядка)" if current_mode == "structured" else "🎯 <b>Дословно 1:1</b> (строго символ в символ)"

    text = (
        f"📸 <b>Получено фото конспекта: {count} шт.</b>\n"
        f"⚙️ <b>Режим:</b> {mode_title}\n\n"
        "Будут еще страницы или приступаем к распознаванию?"
    )
    markup = get_batch_control_keyboard(count, mode=current_mode)

    try:
        if batch.control_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=batch.control_msg_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
                return
            except Exception:
                pass

        sent = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
        batch.control_msg_id = sent.message_id
    except Exception as e:
        logger.error(f"Error notifying user batch: {e}")

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    user_id = message.from_user.id

    # Check authorization
    if not await database.is_user_authorized(user_id):
        await message.answer(
            "🔒 <b>Доступ ограничен</b>\n\n"
            "Чтобы использовать распознавание конспектов, активируйте персональный ключ доступа с помощью команды:\n"
            "<code>/register ВАШ_КЛЮЧ</code>",
            parse_mode="HTML",
            reply_markup=get_unauthorized_keyboard()
        )
        return

    batch = get_or_create_batch(user_id)
    if batch.is_processing:
        await message.answer("⏳ Сейчас выполняется обработка предыдущего конспекта. Пожалуйста, подождите завершения.")
        return

    # Add the highest resolution photo id
    best_photo = message.photo[-1]
    batch.photos.append(best_photo.file_id)

    # Cancel previous pending debounce timer
    if batch.debounce_task and not batch.debounce_task.done():
        batch.debounce_task.cancel()

    # Schedule debounced prompt
    batch.debounce_task = asyncio.create_task(
        debounce_notify_user(user_id=user_id, chat_id=message.chat.id, bot=bot)
    )

@router.callback_query(F.data == "toggle_batch_mode")
async def cb_toggle_batch_mode(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_mode = await database.get_user_mode(user_id)
    new_mode = "exact" if current_mode == "structured" else "structured"
    await database.set_user_mode(user_id, new_mode)

    batch = get_or_create_batch(user_id)
    count = len(batch.photos)
    mode_name = "🎯 Дословно 1:1" if new_mode == "exact" else "🧠 Структурированный"

    mode_title = "🧠 <b>Структурированный конспект</b> (выделение главного, без изменения порядка)" if new_mode == "structured" else "🎯 <b>Дословно 1:1</b> (строго символ в символ)"
    text = (
        f"📸 <b>Получено фото конспекта: {count} шт.</b>\n"
        f"⚙️ <b>Режим:</b> {mode_title}\n\n"
        "Будут еще страницы или приступаем к распознаванию?"
    )

    try:
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_batch_control_keyboard(count, mode=new_mode)
        )
    except Exception:
        pass

    await callback.answer(f"Режим переключен: {mode_name}")

@router.callback_query(F.data == "batch_wait")
async def cb_batch_wait(callback: CallbackQuery):
    batch = get_or_create_batch(callback.from_user.id)
    await callback.answer(f"Жду еще фото. Сейчас в очереди: {len(batch.photos)} шт.", show_alert=True)

@router.callback_query(F.data == "batch_clear")
@router.message(Command("clear"))
@router.message(F.text == "🗑 Очистить очередь")
async def cb_batch_clear(event: CallbackQuery | Message):
    user_id = event.from_user.id
    if user_id in user_batches:
        user_batches[user_id].photos.clear()
        user_batches[user_id].control_msg_id = None
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text("🗑 <b>Очередь фотографий очищена.</b>\n\nВы можете отправить новые фото в любой момент.", parse_mode="HTML")
        await event.answer("Очищено")
    else:
        await event.answer("🗑 <b>Очередь фотографий очищена.</b>\n\nВы можете отправить новые фото в любой момент.", parse_mode="HTML")

@router.callback_query(F.data == "batch_confirm")
async def cb_batch_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    batch = get_or_create_batch(user_id)

    if not batch.photos:
        await callback.answer("Очередь фото пуста. Отправьте хотя бы одно фото!", show_alert=True)
        return

    count = len(batch.photos)
    current_mode = await database.get_user_mode(user_id)
    mode_label = "🧠 Структурированный конспект" if current_mode == "structured" else "🎯 Дословно 1:1"

    text = (
        f"⚙️ <b>Готово к обработке {count} фото</b>\n"
        f"Режим: <b>{mode_label}</b>\n\n"
        "В каком виде вы хотите получить результат?"
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_format_choice_keyboard(count, mode=current_mode)
    )
    await callback.answer()

def chunk_text(text: str, max_chars: int = 3800) -> List[str]:
    chunks = []
    current_chunk = []
    current_length = 0

    paragraphs = text.split("\n\n")
    for p in paragraphs:
        p_len = len(p) + 2
        if current_length + p_len > max_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            if len(p) > max_chars:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i:i+max_chars])
                continue
        current_chunk.append(p)
        current_length += p_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    return chunks

@router.callback_query(F.data.in_(["format_pdf", "format_text", "format_both"]))
async def cb_process_format(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    batch = get_or_create_batch(user_id)
    chosen_format = callback.data.replace("format_", "")

    if not batch.photos:
        await callback.answer("Фото не найдены.", show_alert=True)
        return

    if batch.is_processing:
        await callback.answer("Обработка уже запущена!", show_alert=True)
        return

    batch.is_processing = True
    photos_to_process = list(batch.photos)
    batch.photos.clear()
    count = len(photos_to_process)
    current_mode = await database.get_user_mode(user_id)

    mode_desc = "🧠 Структурирование и выделение главного" if current_mode == "structured" else "🎯 Дословный перевод 1 в 1"

    await callback.message.edit_text(
        f"⏳ <b>ИИ обрабатывает конспект ({count} стр.)...</b>\n\n"
        f"• Режим: <b>{mode_desc}</b>\n"
        "• Сохранение строгого порядка предложений\n"
        "• Обработка формул и форматирование\n\n"
        "<i>Пожалуйста, подождите, это займет от 5 до 25 секунд.</i>",
        parse_mode="HTML"
    )
    await callback.answer()

    pdf_path = None
    try:
        # Download images
        image_bytes_list: List[bytes] = []
        for file_id in photos_to_process:
            file_buf = await bot.download(file_id)
            if file_buf:
                image_bytes_list.append(file_buf.read())

        # Call Gemini OCR with selected mode
        markdown_result = await ocr_service.transcribe_lecture_images(image_bytes_list, mode=current_mode)

        # Output options
        if chosen_format in ("pdf", "both"):
            pdf_path = pdf_service.create_lecture_pdf(markdown_result, filename_prefix=f"lecture_{current_mode}_{user_id}")
            doc_file = FSInputFile(pdf_path, filename=f"Konspekt_{current_mode}_{count}str.pdf")
            mode_caption = "Структурированный конспект" if current_mode == "structured" else "Дословный текст (1:1)"
            await callback.message.answer_document(
                document=doc_file,
                caption=f"📄 <b>Ваш {mode_caption} ({count} стр.)</b>\nОформлен с сохранением порядка предложений.",
                parse_mode="HTML"
            )

        if chosen_format in ("text", "both"):
            chunks = chunk_text(markdown_result)
            for i, chunk in enumerate(chunks, start=1):
                header = f"📝 <b>Часть {i}/{len(chunks)}:</b>\n\n" if len(chunks) > 1 else ""
                try:
                    await callback.message.answer(f"{header}{chunk}", parse_mode="HTML")
                except Exception:
                    plain_header = f"📝 Часть {i}/{len(chunks)}:\n\n" if len(chunks) > 1 else ""
                    await callback.message.answer(f"{plain_header}{chunk}", parse_mode=None)
                await asyncio.sleep(0.3)

        await database.record_usage(user_id=user_id, photos_count=count, output_format=f"{chosen_format}_{current_mode}")

        await callback.message.answer(
            "✅ <b>Готово!</b>\n\n"
            "Вы можете отправить следующую партию фотографий конспекта в любой момент."
        )

    except Exception as e:
        logger.error(f"Error during OCR processing: {e}", exc_info=True)
        safe_error = html.escape(str(e))
        await callback.message.answer(
            f"❌ <b>Произошла ошибка при обработке:</b>\n<code>{safe_error}</code>\n\n"
            "Попробуйте отправить фото повторно.",
            parse_mode="HTML"
        )
    finally:
        batch.is_processing = False
        batch.control_msg_id = None
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass

@router.message(F.text)
async def handle_text_fallback(message: Message):
    user_id = message.from_user.id
    raw_text = message.text.strip()

    if raw_text == "👑 Админ-панель":
        from handlers.admin import cmd_admin
        await cmd_admin(message)
        return

    if raw_text == "🔑 Создать ключ":
        from handlers.admin import cmd_genkey
        await cmd_genkey(message)
        return

    if raw_text.startswith("KEY-") or (len(raw_text) == 14 and "-" in raw_text):
        is_ok, msg = await database.redeem_invite_key(
            key=raw_text,
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        if is_ok:
            user_mode = await database.get_user_mode(user_id)
            is_adm = (user_id == settings.ADMIN_ID)
            from keyboards import get_main_reply_keyboard
            await message.answer(
                f"🎉 {msg}\n\n"
                "Вы успешно зарегистрированы в боте!\n"
                "📸 Отправьте мне фотографии ваших конспектов для распознавания.",
                reply_markup=get_main_reply_keyboard(is_admin=is_adm, mode=user_mode)
            )
            return
        else:
            await message.answer(msg)
            return

    if not await database.is_user_authorized(user_id):
        await message.answer(
            "🔒 <b>Доступ ограничен</b>\n\n"
            "Для использования бота требуется персональный ключ доступа.\n"
            "Введите ваш ключ или команду <code>/register ВАШ_КЛЮЧ</code>.",
            parse_mode="HTML",
            reply_markup=get_unauthorized_keyboard()
        )
        return

    await message.answer(
        "📸 Чтобы оцифровать конспект, <b>отправьте мне фотографии страниц</b> (по одной или альбомом).\n\n"
        "Я объединю их и подготовлю результат в выбранном вами режиме!",
        parse_mode="HTML"
    )
