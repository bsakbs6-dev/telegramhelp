from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import settings
import database
from keyboards import get_admin_main_keyboard, get_admin_back_keyboard

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора.")
        return

    text = (
        "👑 <b>Панель администратора</b>\n\n"
        "Здесь вы можете генерировать пригласительные ключи, просматривать "
        "пользователей и управлять доступом к боту."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    text = (
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите необходимое действие:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Панель закрыта")

@router.callback_query(F.data == "admin_gen_key")
async def cb_gen_key(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    new_key = await database.create_invite_key(created_by=callback.from_user.id)
    text = (
        "✅ <b>Новый ключ доступа создан!</b>\n\n"
        f"Ключ: <code>{new_key}</code>\n\n"
        "<i>Отправьте этот ключ новому пользователю. Он сможет активировать его командой /register или просто отправив боту.</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    await callback.answer("Ключ успешно создан!")

@router.message(Command("genkey"))
async def cmd_genkey(message: Message):
    if not is_admin(message.from_user.id):
        return
    new_key = await database.create_invite_key(created_by=message.from_user.id)
    text = (
        "✅ <b>Новый ключ доступа создан!</b>\n\n"
        f"Ключ: <code>{new_key}</code>\n\n"
        "<i>Нажмите на ключ, чтобы скопировать.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "admin_list_keys")
async def cb_list_keys(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    active_keys = await database.get_active_keys()
    used_keys = await database.get_used_keys()

    text = "📋 <b>Список ключей доступа</b>\n\n"
    if active_keys:
        text += f"🟢 <b>Свободные ключи ({len(active_keys)}):</b>\n"
        for k in active_keys[:15]:
            text += f"• <code>{k['key']}</code> (создан {k['created_at'][:16].replace('T', ' ')})\n"
        if len(active_keys) > 15:
            text += f"...и еще {len(active_keys) - 15}\n"
    else:
        text += "🟢 <b>Свободных ключей нет.</b> Нажмите «Сгенерировать ключ».\n"

    text += "\n"
    if used_keys:
        text += f"⚪ <b>Последние использованные ({len(used_keys)}):</b>\n"
        for k in used_keys[:10]:
            text += f"• <code>{k['key']}</code> — User ID: {k['used_by']}\n"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_list_users")
async def cb_list_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    users = await database.get_users_list()
    text = f"👥 <b>Зарегистрированные пользователи ({len(users)}):</b>\n\n"
    
    keyboard_buttons = []
    for u in users[:15]:
        status_icon = "🟢" if u["is_allowed"] else "🔴 Заблокирован"
        name = u["full_name"] or u["username"] or f"ID: {u['user_id']}"
        text += f"{status_icon} <b>{name}</b> (<code>{u['user_id']}</code>)\n"
        
        if u["user_id"] != settings.ADMIN_ID:
            btn_text = f"❌ Блок {u['user_id']}" if u["is_allowed"] else f"✅ Разблок {u['user_id']}"
            keyboard_buttons.append([
                InlineKeyboardButton(text=btn_text, callback_data=f"toggle_user_{u['user_id']}")
            ])

    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_user_"))
async def cb_toggle_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])
    new_state = await database.toggle_user_access(target_id)
    if new_state is None:
        await callback.answer("Невозможно изменить доступ главного администратора.", show_alert=True)
    else:
        state_str = "разблокирован" if new_state else "заблокирован"
        await callback.answer(f"Пользователь {target_id} {state_str}!", show_alert=True)
        await cb_list_users(callback)

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    stats = await database.get_stats_summary()
    text = (
        "📊 <b>Общая статистика бота</b>\n\n"
        f"👤 Активных пользователей: <b>{stats['total_users']}</b>\n"
        f"🔑 Доступных ключей: <b>{stats['unused_keys']}</b>\n"
        f"⚡ Всего обработок: <b>{stats['total_requests']}</b>\n"
        f"📸 Всего оцифровано фото: <b>{stats['total_photos']}</b>\n"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    await callback.answer()
