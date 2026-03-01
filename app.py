from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import base64

app = Flask(__name__)

# Тильда ключи из .env
TILDA_API_KEY = os.getenv("TILDA_API_KEY")
PROJECT_ID = os.getenv("TILDA_PROJECT_ID")

def download_google_drive(web_content_link):
    """Скачать файл по WebContentLink (Google Drive, публичный)"""
    print(f"[GD] GET {web_content_link}")
    resp = requests.get(web_content_link)
    print(f"[GD] Status: {resp.status_code}, content-type: {resp.headers.get('Content-Type')}")
    resp.raise_for_status()
    return resp.content  # bytes


def upload_image_to_tilda_raw(image_bytes, filename="article.png"):
    """Загрузка байтов в Тильду (publickey В URL!)"""
    # ✅ publickey в URL-параметрах!
    url = f"https://api.tildacdn.info/v1/uploadimage?publickey={TILDA_API_KEY}&projectid={PROJECT_ID}"
    
    files = {"file": (filename, image_bytes, "image/png")}
    
    print("[TILDA] uploadimage...")
    response = requests.post(url, files=files)  # Без data!
    print(f"[TILDA] Status: {response.status_code}")
    print(f"[TILDA] Response: {response.text}")
    
    try:
        result = response.json()
        if result.get("status") == "FOUND" and result.get("result"):
            return result["result"]["url"]
        else:
            print(f"[TILDA] Error in result: {result}")
    except:
        print("[TILDA] JSON parse error")
    
    return None

def upload_image_to_tilda(image_base64, filename="article.png"):
    """Base64 → Тильда"""
    image_data = base64.b64decode(image_base64)
    return upload_image_to_tilda_raw(image_data, filename)
    
def create_tilda_article(title, content_html, image_url, **kwargs):
    """Создание статьи в Тильде"""
    url = "https://api.tildacdn.info/v1/postadd"
    
    payload = {
        "publickey": TILDA_API_KEY,
        "projectid": PROJECT_ID,
        "title": title,
        "content": content_html,
        "img": image_url,
        "date": kwargs.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "author": kwargs.get("author", "Decorewood Team"),
        "seo_title": kwargs.get("seo_title", title[:60]),
        "seo_description": kwargs.get("seo_desc", content_html[:155]), 
        "seo_keywords": kwargs.get("seo_keywords", "шпон,панели,отделка"),
        "published": "1",
        "sort": "0"
    }
    
    response = requests.post(url, json=payload)
    return response.json()

@app.route('/post-to-tilda', methods=['POST'])
def post_article():
    """Основной endpoint - Google Drive + base64"""
    data = request.json
    
    title = data['title']
    content = data['content_html']
    
    image_url = data.get('image_url')

    if image_url:
        print("🔗 Using image_url:", image_url)
        image_bytes = download_google_drive(image_url)
        tilda_image_url = upload_image_to_tilda_raw(image_bytes)
    else:
        print("🖼️ Using base64 image")
        image_b64 = data['image_base64']
        tilda_image_url = upload_image_to_tilda(image_b64)
    
    if not tilda_image_url:
        return jsonify({"error": "❌ Image upload to Tilda failed"}), 400
    
    # Создаем статью
    result = create_tilda_article(title, content, tilda_image_url)
    
    return jsonify({
        "success": True,
        "tilda_url": result.get("result", {}).get("url", ""),
        "image_url": tilda_image_url,
        "debug": result  # Для отладки
    })


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "alive"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))

    app.run(host='0.0.0.0', port=port)





