import logging
import asyncio
from typing import List
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — интеллектуальный ассистент по оцифровке, распознаванию и структурированию рукописных и печатных конспектов, лекций и учебных материалов.

Твоя задача — внимательно изучить полученные изображения страниц конспекта (в порядке их следования) и преобразовать их в чистый, безупречно структурированный текст.

ОСНОВНЫЕ ПРАВИЛА И ТРЕБОВАНИЯ:
1. ОПРЕДЕЛЕНИЕ СТРУКТУРЫ И ГРАНИЦ ЛЕКЦИЙ:
   - Внимательно определи, где НАЧАЛО лекции (название темы, предмет, дата, ФИО преподавателя, вводная часть).
   - Если в материале содержится несколько разных лекций или не связанных тем, четко раздели их разделителем '---' и выдели отдельные заголовки.
   - Определи, где КОНЕЦ лекции (выводы, заключение, вопросы для самопроверки, домашнее задание или логическое завершение темы).

2. ТОЧНОСТЬ РАСПОЗНАВАНИЯ:
   - Точно переведи рукописный и печатный текст на русском и других языках.
   - Исправляй очевидные грамматические помарки и опечатки рукописного почерка, не искажая смысл.
   - Склеивай слова и предложения, разорванные переносом строк или переходом с одной страницы/фотографии на следующую.

3. ФОРМАТИРОВАНИЕ:
   - Используй Markdown:
     * # Заголовок лекции / Темы
     * ## Основные разделы и параграфы
     * ### Подпункты, теоремы, определения
     * **Жирный шрифт** для ключевых терминов, дат, формулировок
     * Маркированные и нумерованные списки для перечислений
     * Блоки кода или формул для математических выражений, химических формул, программного кода.
     * Если есть схемы или таблицы — представь их в виде аккуратных Markdown-таблиц или списков.

4. ЯЗЫК:
   - Русский язык (или исходный язык конспекта).
   - Не добавляй от себя лишних вводных фраз вроде "Вот ваш конспект:". Сразу начинай со структурированного текста.
"""

class OCRService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.primary_model = settings.PRIMARY_MODEL
        self.fallback_model = settings.FALLBACK_MODEL

    async def transcribe_lecture_images(self, image_data_list: List[bytes]) -> str:
        """
        Sends photos to Gemini for transcription and lecture structuring.
        Automatically falls back if primary model is unavailable.
        """
        parts = []
        for i, img_bytes in enumerate(image_data_list, start=1):
            part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            parts.append(part)

        user_content = [
            *parts,
            f"Перед тобой {len(image_data_list)} фото конспекта/лекции. Пожалуйста, выполни полное распознавание текста, определи структуру, начало и конец лекции, упорядочи материал и оформи его в качественный и читаемый вид по инструкции."
        ]

        # Try primary model, fallback if error occurs
        models_to_try = [self.primary_model, self.fallback_model]
        last_error = None

        for model_name in models_to_try:
            try:
                logger.info(f"Processing {len(image_data_list)} images with model {model_name}...")
                response = await self.client.aio.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                    )
                )
                if response and response.text:
                    return response.text.strip()
                else:
                    raise ValueError("Empty response received from Gemini.")
            except Exception as e:
                logger.warning(f"Error with model {model_name}: {e}. Trying fallback if available...")
                last_error = e
                await asyncio.sleep(1)

        raise RuntimeError(f"Не удалось распознать изображения: {last_error}")

ocr_service = OCRService()
