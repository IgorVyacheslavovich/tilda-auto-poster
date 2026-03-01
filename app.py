from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import base64

app = Flask(__name__)

# Тильда ключи из .env
TILDA_API_KEY = os.getenv("TILDA_API_KEY")
PROJECT_ID = os.getenv("TILDA_PROJECT_ID")

def upload_image_to_tilda(image_base64, filename="article.png"):
    """Загрузка картинки из base64"""
    url = "https://api.tilda.cc/v1/uploadimage"
    
    # Base64 → bytes
    image_data = base64.b64decode(image_base64)
    
    files = {"file": (filename, image_data, "image/png")}
    data = {"publickey": TILDA_API_KEY, "projectid": PROJECT_ID}
    
    response = requests.post(url, files=files, data=data)
    result = response.json()
    
    return result["result"]["url"] if result.get("result") else None

def create_tilda_article(title, content_html, image_url):
    """Создание статьи в Тильде"""
    url = "https://api.tilda.cc/v1/postadd"
    
    payload = {
        "publickey": TILDA_API_KEY,
        "projectid": PROJECT_ID,
        "title": title,
        "content": content_html,
        "img": image_url,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    response = requests.post(url, json=payload)
    return response.json()

@app.route('/post-to-tilda', methods=['POST'])
def post_article():
    data = request.json
    
    # Из Make.com приходят данные
    title = data['title']
    content = data['content_html']
    image_b64 = data['image_base64']  # из OpenAI Image
    
    # 1. Загрузка картинки
    image_url = upload_image_to_tilda(image_b64, "article.png")
    
    if not image_url:
        return jsonify({"error": "Image upload failed"}), 400
    
    # 2. Создание статьи
    result = create_tilda_article(title, content, image_url)
    
    return jsonify({
        "success": True,
        "tilda_url": result.get("result", {}).get("url", ""),
        "image_url": image_url
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)