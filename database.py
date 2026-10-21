import os
import aiosqlite
import secrets
import string
from datetime import datetime
from config import settings

def generate_random_key(prefix: str = "KEY-", length: int = 10) -> str:
    chars = string.ascii_uppercase + string.digits
    rand_str = "".join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}{rand_str}"

async def init_db():
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                is_admin BOOLEAN DEFAULT 0,
                is_allowed BOOLEAN DEFAULT 1,
                ocr_mode TEXT DEFAULT 'structured',
                registered_at TEXT
            )
        """)
        
        # Upgrade schema if column ocr_mode doesn't exist yet
        try:
            await db.execute("ALTER TABLE users ADD COLUMN ocr_mode TEXT DEFAULT 'structured'")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_keys (
                key TEXT PRIMARY KEY,
                created_by INTEGER,
                created_at TEXT,
                is_used BOOLEAN DEFAULT 0,
                used_by INTEGER,
                used_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                photos_count INTEGER,
                output_format TEXT,
                created_at TEXT
            )
        """)
        
        # Ensure Super Admin is always registered and authorized
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, is_admin, is_allowed, registered_at)
            VALUES (?, 'admin', 'Administrator', 1, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET is_admin = 1, is_allowed = 1
        """, (settings.ADMIN_ID, datetime.now().isoformat()))
        
        await db.commit()

async def is_user_authorized(user_id: int) -> bool:
    if user_id == settings.ADMIN_ID:
        return True
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute(
            "SELECT is_allowed FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == 1:
                return True
    return False

async def get_user_mode(user_id: int) -> str:
    """Returns 'structured' or 'exact'."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT ocr_mode FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
    return "structured"

async def set_user_mode(user_id: int, mode: str):
    """Sets mode: 'structured' or 'exact'."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("UPDATE users SET ocr_mode = ? WHERE user_id = ?", (mode, user_id))
        await db.commit()

async def create_invite_key(created_by: int) -> str:
    key = generate_random_key()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            "INSERT INTO invite_keys (key, created_by, created_at, is_used) VALUES (?, ?, ?, 0)",
            (key, created_by, now)
        )
        await db.commit()
    return key

async def redeem_invite_key(key: str, user_id: int, username: str | None, full_name: str | None) -> tuple[bool, str]:
    cleaned_key = key.strip()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute(
            "SELECT is_used FROM invite_keys WHERE key = ?", (cleaned_key,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, "❌ Неверный ключ доступа. Проверьте правильность ввода."
            if row[0] == 1:
                return False, "⚠️ Этот ключ доступа уже был активирован ранее."

        # Mark key as used
        await db.execute(
            "UPDATE invite_keys SET is_used = 1, used_by = ?, used_at = ? WHERE key = ?",
            (user_id, now, cleaned_key)
        )
        # Register user
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, is_admin, is_allowed, registered_at)
            VALUES (?, ?, ?, 0, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET is_allowed = 1, username = ?, full_name = ?
        """, (user_id, username or "", full_name or "", now, username or "", full_name or ""))
        
        await db.commit()
        return True, "✅ Доступ успешно получен! Добро пожаловать."

async def get_active_keys() -> list[dict]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT key, created_at FROM invite_keys WHERE is_used = 0 ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_used_keys() -> list[dict]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT key, used_by, used_at FROM invite_keys WHERE is_used = 1 ORDER BY used_at DESC LIMIT 20"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_users_list() -> list[dict]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, full_name, is_admin, is_allowed, registered_at FROM users ORDER BY registered_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def toggle_user_access(user_id: int) -> bool | None:
    if user_id == settings.ADMIN_ID:
        return None # cannot revoke root admin
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT is_allowed FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            new_val = 0 if row[0] == 1 else 1
        await db.execute("UPDATE users SET is_allowed = ? WHERE user_id = ?", (new_val, user_id))
        await db.commit()
        return bool(new_val)

async def delete_key(key: str) -> bool:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("DELETE FROM invite_keys WHERE key = ?", (key.strip(),))
        await db.commit()
        return True

async def record_usage(user_id: int, photos_count: int, output_format: str):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            "INSERT INTO usage_stats (user_id, photos_count, output_format, created_at) VALUES (?, ?, ?, ?)",
            (user_id, photos_count, output_format, now)
        )
        await db.commit()

async def get_stats_summary() -> dict:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_allowed = 1") as c1:
            total_users = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM invite_keys WHERE is_used = 0") as c2:
            unused_keys = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*), COALESCE(SUM(photos_count), 0) FROM usage_stats") as c3:
            req_count, total_photos = await c3.fetchone()
    return {
        "total_users": total_users,
        "unused_keys": unused_keys,
        "total_requests": req_count,
        "total_photos": total_photos
    }
