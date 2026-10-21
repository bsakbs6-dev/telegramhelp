from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

def get_main_reply_keyboard(is_admin: bool, mode: str = "structured") -> ReplyKeyboardMarkup:
    """Persistent bottom panel menu in chat."""
    mode_btn_text = "⚙️ Режим: 🧠 Конспект" if mode == "structured" else "⚙️ Режим: 🎯 Дословно 1:1"
    
    keyboard = [
        [
            KeyboardButton(text="📸 Отправить конспект"),
            KeyboardButton(text=mode_btn_text)
        ]
    ]
    if is_admin:
        keyboard.append([
            KeyboardButton(text="👑 Админ-панель"),
            KeyboardButton(text="🔑 Создать ключ"),
            KeyboardButton(text="ℹ️ Помощь")
        ])
    else:
        keyboard.append([
            KeyboardButton(text="🗑 Очистить очередь"),
            KeyboardButton(text="ℹ️ Помощь")
        ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_unauthorized_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Ввести ключ доступа", callback_data="enter_key_prompt")]
    ])

def get_batch_control_keyboard(count: int, mode: str = "structured") -> InlineKeyboardMarkup:
    mode_text = "🧠 Структура" if mode == "structured" else "🎯 Дословно 1:1"
    next_mode_text = "Переключить на: 🎯 Дословно 1:1" if mode == "structured" else "Переключить на: 🧠 Структуру"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🚀 Распознать ({count} фото)", callback_data="batch_confirm")
        ],
        [
            InlineKeyboardButton(text=f"🔄 {next_mode_text}", callback_data="toggle_batch_mode")
        ],
        [
            InlineKeyboardButton(text="➕ Жду ещё фото...", callback_data="batch_wait"),
            InlineKeyboardButton(text="🗑 Очистить", callback_data="batch_clear")
        ]
    ])

def get_mode_choice_keyboard(current_mode: str = "structured") -> InlineKeyboardMarkup:
    str_mark = "✅ " if current_mode == "structured" else ""
    exact_mark = "✅ " if current_mode == "exact" else ""

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{str_mark}🧠 Структурированный (выделить главное)",
                callback_data="set_mode_structured"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{exact_mark}🎯 Дословно 1:1 (символ в символ)",
                callback_data="set_mode_exact"
            )
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="close_mode_menu")
        ]
    ])

def get_format_choice_keyboard(count: int, mode: str = "structured") -> InlineKeyboardMarkup:
    mode_label = "🧠 Структура" if mode == "structured" else "🎯 Дословно 1:1"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 В PDF документ", callback_data="format_pdf"),
            InlineKeyboardButton(text="💬 Текстом в чат", callback_data="format_text")
        ],
        [
            InlineKeyboardButton(text="📑 PDF + Текст в чат", callback_data="format_both")
        ],
        [
            InlineKeyboardButton(text=f"⚙️ Режим: {mode_label}", callback_data="toggle_batch_mode")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="batch_clear")
        ]
    ])

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Сгенерировать ключ", callback_data="admin_gen_key"),
            InlineKeyboardButton(text="📋 Список ключей", callback_data="admin_list_keys")
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_list_users"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="🔄 Закрыть панель", callback_data="admin_close")
        ]
    ])

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_back")]
    ])
