from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_unauthorized_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Ввести ключ доступа", callback_data="enter_key_prompt")]
    ])

def get_batch_control_keyboard(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🚀 Распознать ({count} фото)", callback_data="batch_confirm")
        ],
        [
            InlineKeyboardButton(text="➕ Жду ещё фото...", callback_data="batch_wait"),
            InlineKeyboardButton(text="🗑 Очистить", callback_data="batch_clear")
        ]
    ])

def get_format_choice_keyboard(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 В PDF документ", callback_data="format_pdf"),
            InlineKeyboardButton(text="💬 Текстом в чат", callback_data="format_text")
        ],
        [
            InlineKeyboardButton(text="📑 PDF + Текст в чат", callback_data="format_both")
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
