import logging
import asyncio
from typing import List
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_STRUCTURED = """Ты — интеллектуальный ассистент по оцифровке и структурированию конспектов и лекций.

Твоя задача — изучить полученные изображения страниц конспекта и преобразовать их в чистый структурированный текст.

ОСНОВНЫЕ ПРАВИЛА:
1. СТРОГИЙ ПОРЯДОК:
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО МЕНЯТЬ МЕСТАМИ ПРЕДЛОЖЕНИЯ И АБЗАЦЫ! Сохраняй исходный порядок мыслей, предложений и абзацев в точности, как в источнике.
2. ВЫДЕЛЕНИЕ ГЛАВНОГО:
   - Определи НАЧАЛО лекции (тема, предмет, дата, преподаватель) и КОНЕЦ лекции (выводы, вопросы, домашнее задание, завершение темы).
   - Выдели визуально главное:
     * # Заголовок темы
     * ## Основные разделы
     * ### Подпункты
     * **Жирный шрифт** для ключевых определений, терминов, дат и формул
     * Списки (маркированные или нумерованные) для перечислений
3. ТОЧНОСТЬ:
   - Исправляй очевидные опечатки рукописного почерка, сохраняя точный смысл.
   - Склеивай слова и предложения, разорванные переносом строк на границе страниц.
4. Выдавай сразу готовый материал без лишних вводных фраз вроде "Вот ваш конспект:".
"""

SYSTEM_PROMPT_EXACT = """Ты — высокоточный профессиональный OCR-инструмент для дословного перевода текста с фотографий.

ТВОЯ ЗАДАЧА:
1. Распознать и перевести весь текст строго 1 К 1 СИМВОЛ В СИМВОЛ, как написано на фото.
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
   - Менять местами предложения, слова или абзацы.
   - Перефразировать, редактировать или придумывать текст.
   - Сокращать текст, делать выжимки или убирать фрагменты.
3. Сохраняй точный авторский порядок изложения, пунктуацию, регистр и деление на строки/абзацы.
4. Аккуратно склеивай только слова, разорванные знаком переноса строки на краю страницы.
5. Не добавляй никаких приветствий, пояснений или комментариев от себя. Выдавай ТОЛЬКО исходный текст.
"""

class OCRService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.primary_model = settings.PRIMARY_MODEL
        self.fallback_model = settings.FALLBACK_MODEL

    async def transcribe_lecture_images(self, image_data_list: List[bytes], mode: str = "structured") -> str:
        """
        Sends photos to Gemini for transcription.
        mode can be:
          - 'structured': Highlights headings/definitions without altering sentence order.
          - 'exact': Strict 1:1 character-by-character transcription.
        """
        system_instruction = SYSTEM_PROMPT_EXACT if mode == "exact" else SYSTEM_PROMPT_STRUCTURED

        parts = []
        for i, img_bytes in enumerate(image_data_list, start=1):
            part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            parts.append(part)

        if mode == "exact":
            instruction_text = (
                f"Перед тобой {len(image_data_list)} фото. Выполни строгое дословное распознавание 1 в 1 символ к символу. "
                "Не меняй порядок слов и предложений, не сокращай текст."
            )
        else:
            instruction_text = (
                f"Перед тобой {len(image_data_list)} фото конспекта. Структурируй материал: выдели начало и конец лекции, "
                "заголовки, формулы и ключевые термины, НО НЕ МЕНЯЙ МЕСТАМИ ПРЕДЛОЖЕНИЯ И АБЗАЦЫ."
            )

        user_content = [*parts, instruction_text]
        models_to_try = [self.primary_model, self.fallback_model]
        last_error = None

        for model_name in models_to_try:
            for attempt in range(1, 4):
                try:
                    logger.info(f"Processing {len(image_data_list)} images with {model_name} (mode={mode}, attempt {attempt}/3)...")
                    response = await self.client.aio.models.generate_content(
                        model=model_name,
                        contents=user_content,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.1 if mode == "exact" else 0.2,
                        )
                    )
                    if response and response.text:
                        return response.text.strip()
                    else:
                        raise ValueError("Empty response received from Gemini.")
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    logger.warning(f"Error with model {model_name} on attempt {attempt}: {e}")

                    if "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
                        if attempt < 3:
                            wait_time = attempt * 2
                            logger.info(f"Temporary demand spike on {model_name}. Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    break

        raise RuntimeError(f"Не удалось распознать изображения: {last_error}")

ocr_service = OCRService()
