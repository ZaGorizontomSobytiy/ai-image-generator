#!/usr/bin/env python3
"""
Flask веб-приложение для генерации изображений с AI
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import threading

from gigachat_enhancer import enhance_prompt
from image_generator_core import generate_image

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
CORS(app)

# Глобальные переменные для отслеживания прогресса
generation_status = {
    "status": "idle",  # idle, enhancing, generating, done, error
    "progress": 0,
    "message": "",
    "image_path": None,
    "original_prompt": "",
    "enhanced_prompt": "",
    "error": None
}

# Предустановленные стили
STYLES = {
    "none": {"name": "Без стиля", "suffix": ""},
    "photorealistic": {
        "name": "Фотореализм", 
        "suffix": "photorealistic, high detail, professional photography, studio lighting"
    },
    "anime": {
        "name": "Аниме", 
        "suffix": "anime style, detailed anime art, vibrant colors, manga illustration"
    },
    "watercolor": {
        "name": "Акварель", 
        "suffix": "watercolor painting, soft colors, artistic, traditional art"
    },
    "cyberpunk": {
        "name": "Киберпанк", 
        "suffix": "cyberpunk style, neon lights, futuristic, dark atmosphere"
    },
    "pixel": {
        "name": "Пиксель-арт", 
        "suffix": "pixel art, 8-bit style, retro gaming aesthetic"
    },
    "oil": {
        "name": "Масляная живопись", 
        "suffix": "oil painting, classic art style, textured brushstrokes"
    }
}


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', styles=STYLES)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API эндпоинт для генерации изображений"""
    global generation_status
    
    data = request.json
    user_prompt = data.get('prompt', '').strip()
    style_key = data.get('style', 'none')
    provider = data.get('provider', 'proxyapi')
    
    if not user_prompt:
        return jsonify({"error": "Промпт не может быть пустым"}), 400
    
    # Сброс статуса
    generation_status = {
        "status": "starting",
        "progress": 0,
        "message": "Начинаем генерацию...",
        "image_path": None,
        "original_prompt": user_prompt,
        "enhanced_prompt": "",
        "error": None
    }
    
    # Запуск генерации в фоне
    thread = threading.Thread(
        target=generate_image_background,
        args=(user_prompt, style_key, provider)
    )
    thread.start()
    
    return jsonify({"success": True, "message": "Генерация запущена"})


def generate_image_background(user_prompt, style_key, provider):
    """Фоновая генерация изображения"""
    global generation_status
    
    try:
        # Шаг 1: Улучшение промпта
        generation_status["status"] = "enhancing"
        generation_status["progress"] = 20
        generation_status["message"] = "🤖 GigaChat улучшает промпт..."
        
        style = STYLES.get(style_key, STYLES["none"])
        enhanced = enhance_prompt(user_prompt, style["suffix"])
        
        generation_status["enhanced_prompt"] = enhanced
        generation_status["progress"] = 40
        generation_status["message"] = "✓ Промпт улучшен!"
        
        # Шаг 2: Генерация изображения
        generation_status["status"] = "generating"
        generation_status["progress"] = 60
        generation_status["message"] = f"🎨 Генерируем изображение через {provider.upper()}..."
        
        image_path = generate_image(enhanced, provider)
        
        # Готово
        generation_status["status"] = "done"
        generation_status["progress"] = 100
        generation_status["message"] = "✓ Изображение готово!"
        generation_status["image_path"] = str(image_path)
        
    except Exception as e:
        generation_status["status"] = "error"
        generation_status["error"] = str(e)
        generation_status["message"] = f"✗ Ошибка: {str(e)}"


@app.route('/api/status')
def api_status():
    """Получение статуса генерации"""
    return jsonify(generation_status)


@app.route('/api/gallery')
def api_gallery():
    """Получение списка последних сгенерированных изображений"""
    images = []
    
    for provider in ["proxyapi", "openrouter"]:
        img_dir = Path(f"generated_images/{provider}")
        if img_dir.exists():
            for img_file in sorted(img_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                images.append({
                    "path": str(img_file),
                    "filename": img_file.name,
                    "provider": provider
                })
    
    return jsonify(images)


@app.route('/images/<provider>/<filename>')
def serve_image(provider, filename):
    """Отдача сгенерированных изображений"""
    return send_from_directory(f'generated_images/{provider}', filename)


if __name__ == '__main__':
    print("=" * 60)
    print("AI Image Generator Web App")
    print("=" * 60)
    print("\nServer started!")
    print("Open: http://localhost:5000")
    print("\n" + "=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

