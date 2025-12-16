#!/usr/bin/env python3
"""
Модуль для генерации изображений через ProxyAPI и OpenRouter
"""

import os
import base64
import requests
from datetime import datetime
from pathlib import Path
from openai import OpenAI


def get_proxy_api_key():
    """Получает ключ ProxyAPI из переменной окружения"""
    api_key = os.getenv("PROXY_API")
    if not api_key:
        raise ValueError("PROXY_API не установлен в .env")
    return api_key


def get_openrouter_api_key():
    """Получает ключ OpenRouter из переменной окружения"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY не установлен в .env")
    return api_key


def create_output_directory(provider="proxyapi"):
    """Создает директорию для сохранения изображений"""
    output_dir = Path(f"generated_images/{provider}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_image_proxyapi(prompt, output_dir=None):
    """
    Генерирует изображение через ProxyAPI
    
    Args:
        prompt: Промпт для генерации
        output_dir: Директория для сохранения (опционально)
        
    Returns:
        Path: Путь к сохраненному изображению
    """
    if output_dir is None:
        output_dir = create_output_directory("proxyapi")
    
    api_key = get_proxy_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.proxyapi.ru/openai/v1"
    )
    
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt
    )
    
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_prompt = safe_prompt.replace(' ', '_')
    filename = f"{timestamp}_{safe_prompt}.png"
    filepath = output_dir / filename
    
    with open(filepath, 'wb') as f:
        f.write(image_bytes)
    
    return filepath


def _extract_data_urls_from_message(message):
    """
    Возвращает список data URL картинок из assistant message.
    Поддерживает структуру OpenRouter: message.images[*].image_url.url
    """
    urls = []

    images = getattr(message, "images", None)
    if not images:
        try:
            md = message.model_dump()  # pydantic v2
        except Exception:
            md = message if isinstance(message, dict) else None
        if md and isinstance(md, dict):
            images = md.get("images")

    if not images:
        return urls

    for img in images:
        # img может быть dict или объектом
        if isinstance(img, dict):
            url = (img.get("image_url") or {}).get("url")
        else:
            image_url = getattr(img, "image_url", None)
            url = getattr(image_url, "url", None) if image_url else None

        if url and isinstance(url, str) and url.startswith("data:image/"):
            urls.append(url)

    return urls


def generate_image_openrouter(prompt, output_dir=None):
    """
    Генерирует изображение через OpenRouter (Nano Banana - Gemini 2.5 Flash Image)
    
    Args:
        prompt: Промпт для генерации
        output_dir: Директория для сохранения (опционально)
        
    Returns:
        Path: Путь к сохраненному изображению
    """
    if output_dir is None:
        output_dir = create_output_directory("openrouter")
    
    api_key = get_openrouter_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    # Используем Gemini 2.5 Flash Image (Nano Banana) для генерации
    res = client.chat.completions.create(
        model="google/gemini-2.5-flash-image",
        messages=[{"role": "user", "content": prompt}],
        modalities=["image", "text"]
    )
    
    message = res.choices[0].message
    data_urls = _extract_data_urls_from_message(message)

    if not data_urls:
        try:
            debug = message.model_dump()
        except Exception:
            debug = {"message_str": str(message)}
        raise ValueError(f"Не удалось найти images[].image_url.url в ответе. Debug: {debug}")

    data_url = data_urls[0]
    
    # Декодируем base64
    b64 = data_url.split("base64,", 1)[1]
    image_bytes = base64.b64decode(b64)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_prompt = safe_prompt.replace(' ', '_')
    filename = f"{timestamp}_{safe_prompt}.png"
    filepath = output_dir / filename
    
    with open(filepath, 'wb') as f:
        f.write(image_bytes)
    
    return filepath


def generate_image(prompt, provider="proxyapi"):
    """
    Универсальная функция генерации изображений
    
    Args:
        prompt: Промпт для генерации
        provider: "proxyapi" или "openrouter"
        
    Returns:
        Path: Путь к сохраненному изображению
    """
    if provider == "proxyapi":
        return generate_image_proxyapi(prompt)
    elif provider == "openrouter":
        return generate_image_openrouter(prompt)
    else:
        raise ValueError(f"Неизвестный провайдер: {provider}")

