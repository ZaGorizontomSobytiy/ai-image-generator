#!/usr/bin/env python3
"""
CLI приложение для генерации изображений через OpenRouter (Gemini Flash Image)
С улучшением промптов через GigaChat
"""

import os
import sys
import base64
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from gigachat import GigaChat


def load_environment():
    """Загружает переменные окружения из .env файла"""
    load_dotenv()


def get_openrouter_api_key():
    """Получает ключ OpenRouter из переменной окружения"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Ошибка: Переменная окружения OPENROUTER_API_KEY не установлена")
        print("Добавьте ключ в файл .env: OPENROUTER_API_KEY=ваш_ключ")
        sys.exit(1)
    return api_key


def get_gigachat_credentials():
    """Получает ключ авторизации GigaChat из переменной окружения"""
    credentials = os.getenv("GIGACHAT_AUTH_KEY")
    if not credentials:
        print("Ошибка: Переменная окружения GIGACHAT_AUTH_KEY не установлена")
        print("Добавьте ключ в файл .env: GIGACHAT_AUTH_KEY=ваш_ключ")
        sys.exit(1)
    return credentials


def enhance_prompt_with_gigachat(simple_prompt, max_length=250):
    """
    Улучшает простой промпт через GigaChat для генерации изображений
    
    Args:
        simple_prompt: Простой промпт от пользователя
        max_length: Максимальная длина улучшенного промпта (по умолчанию 250 символов)
        
    Returns:
        str: Улучшенный детализированный промпт
    """
    print(f"\n🤖 GigaChat улучшает промпт...")
    
    try:
        credentials = get_gigachat_credentials()
        
        with GigaChat(
            credentials=credentials, 
            verify_ssl_certs=False,
            model="GigaChat"  # Базовая модель (дешевле чем GigaChat-Pro)
        ) as giga:
            system_instruction = f"""Ты - эксперт по созданию промптов для генерации изображений.
Твоя задача: взять простой промпт и превратить его в КРАТКОЕ, но детализированное описание для AI-генератора.

ВАЖНО: Ответ должен быть не длиннее {max_length} символов!

Добавь КРАТКО:
- Стиль (фотореализм/арт/акварель)
- Ключевые детали композиции
- Освещение и настроение

Ответь ТОЛЬКО улучшенным промптом, БЕЗ пояснений и лишних слов."""

            prompt = f"{system_instruction}\n\nПромпт: {simple_prompt}\n\nУлучшенный:"
            
            # GigaChat.chat() принимает только строку промпта
            response = giga.chat(prompt)
            enhanced = response.choices[0].message.content.strip()
            
            # Обрезаем если слишком длинный
            if len(enhanced) > max_length:
                enhanced = enhanced[:max_length].rsplit(' ', 1)[0] + "..."
            
            print(f"✓ Промпт улучшен! (длина: {len(enhanced)} символов)")
            return enhanced
            
    except Exception as e:
        print(f"\n⚠️ Ошибка GigaChat: {str(e)}")
        print(f"Используем оригинальный промпт...")
        return simple_prompt


def create_output_directory():
    """Создает директорию для сохранения изображений"""
    output_dir = Path("generated_images/openrouter")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_image(client, prompt, output_dir):
    """Генерирует изображение по промпту через OpenRouter и сохраняет его"""
    print(f"\nГенерация изображения по промпту: '{prompt}'...")
    
    try:
        res = client.chat.completions.create(
            model="google/gemini-2.5-flash-image-preview",
            messages=[{"role": "user", "content": prompt}],
            modalities=["image", "text"]
        )
        
        # Получаем изображение из ответа
        message = res.choices[0].message
        
        # Пробуем разные варианты структуры ответа
        data_url = None
        
        # Вариант 1: images существует
        if hasattr(message, 'images') and message.images:
            image_data = message.images[0]
            if isinstance(image_data, dict):
                data_url = image_data.get("url") or image_data.get("imageUrl", {}).get("url")
            else:
                data_url = getattr(image_data, 'url', None)
        
        # Вариант 2: content содержит изображение
        elif hasattr(message, 'content') and isinstance(message.content, list):
            for item in message.content:
                if isinstance(item, dict) and 'image_url' in item:
                    data_url = item['image_url'].get('url')
                    break
        
        # Вариант 3: content это строка с base64
        elif hasattr(message, 'content') and isinstance(message.content, str):
            if message.content.startswith('data:image'):
                data_url = message.content
        
        if not data_url:
            raise ValueError(f"Не удалось найти изображение в ответе. Структура: {dir(message)}")
        
        b64 = data_url.split("base64,", 1)[1]
        image_bytes = base64.b64decode(b64)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"{timestamp}_{safe_prompt}.png"
        filepath = output_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        print(f"\n✓ Изображение успешно сохранено: {filepath.absolute()}")
        return filepath
        
    except Exception as e:
        print(f"\n✗ Ошибка при генерации изображения: {str(e)}")
        sys.exit(1)


def main():
    """Основная функция CLI приложения"""
    print("=" * 60)
    print("Генератор изображений через OpenRouter (Gemini Flash)")
    print("=" * 60)
    
    load_environment()
    
    api_key = get_openrouter_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    output_dir = create_output_directory()
    print(f"\nИзображения будут сохранены в: {output_dir.absolute()}")
    
    print("\n" + "-" * 60)
    user_prompt = input("Введите промпт для генерации изображения: ").strip()
    
    if not user_prompt:
        print("Ошибка: Промпт не может быть пустым")
        sys.exit(1)
    
    # Улучшение промпта через GigaChat
    enhanced_prompt = enhance_prompt_with_gigachat(user_prompt)
    
    # Показываем оба варианта
    print("\n" + "=" * 60)
    print("📝 ПРОМПТЫ:")
    print("-" * 60)
    print(f"Оригинал:   {user_prompt}")
    print(f"\nУлучшенный: {enhanced_prompt}")
    print("=" * 60)
    
    generate_image(client, enhanced_prompt, output_dir)
    
    print("\n" + "=" * 60)
    print("Готово!")
    print("=" * 60)


if __name__ == "__main__":
    main()
