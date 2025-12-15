#!/usr/bin/env python3
"""
Модуль для улучшения промптов через GigaChat API
"""

import os
from gigachat import GigaChat


def get_gigachat_credentials():
    """Получает ключ авторизации GigaChat из переменной окружения"""
    credentials = os.getenv("GIGACHAT_AUTH_KEY")
    if not credentials:
        raise ValueError("GIGACHAT_AUTH_KEY не установлен в .env")
    return credentials


def enhance_prompt(simple_prompt, style_suffix="", max_length=250):
    """
    Улучшает простой промпт через GigaChat для генерации изображений
    
    Args:
        simple_prompt: Простой промпт от пользователя
        style_suffix: Дополнение стиля к промпту
        max_length: Максимальная длина улучшенного промпта
        
    Returns:
        str: Улучшенный детализированный промпт
    """
    try:
        credentials = get_gigachat_credentials()
        
        with GigaChat(
            credentials=credentials, 
            verify_ssl_certs=False,
            model="GigaChat"
        ) as giga:
            system_instruction = f"""Ты - эксперт по созданию промптов для генерации изображений.
Твоя задача: взять простой промпт и превратить его в КРАТКОЕ, но детализированное описание для AI-генератора.

ВАЖНО: Ответ должен быть не длиннее {max_length} символов!

Добавь КРАТКО:
- Ключевые детали композиции
- Освещение и настроение
- Технические детали

{f'ОБЯЗАТЕЛЬНО учти стиль: {style_suffix}' if style_suffix else ''}

Ответь ТОЛЬКО улучшенным промптом, БЕЗ пояснений и лишних слов."""

            prompt = f"{system_instruction}\n\nПромпт: {simple_prompt}\n\nУлучшенный:"
            
            response = giga.chat(prompt)
            enhanced = response.choices[0].message.content.strip()
            
            # Обрезаем если слишком длинный
            if len(enhanced) > max_length:
                enhanced = enhanced[:max_length].rsplit(' ', 1)[0] + "..."
            
            # Добавляем стиль к улучшенному промпту
            if style_suffix:
                enhanced = f"{enhanced}, {style_suffix}"
            
            return enhanced
            
    except Exception as e:
        print(f"Ошибка GigaChat: {str(e)}")
        # Возвращаем оригинал + стиль
        return f"{simple_prompt}, {style_suffix}" if style_suffix else simple_prompt

