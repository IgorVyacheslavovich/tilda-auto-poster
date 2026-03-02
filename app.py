import cloudinary
import cloudinary.uploader
from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import base64

app = Flask(__name__)

# Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Тильда (проверь .env!)
TILDA_PUBLIC_KEY = os.getenv("TILDA_PUBLIC_KEY")
TILDA_SECRET_KEY = os.getenv("TILDA_SECRET_KEY")
TILDA_PROJECT_ID = os.getenv("TILDA_PROJECT_ID")

def upload_to_cloudinary(image_bytes, public_id="article"):
    """Binary → Cloudinary (фикс format auto)"""
    # Убираем format="auto" — Cloudinary сам определит
    result = cloudinary.uploader.upload(
        image_bytes,
        folder="tilda_posts",
        public_id=public_id,
        quality="auto"  # Только качество
    )
    print(f"☁️ Cloudinary: {result['secure_url']}")
    return result['secure_url']

def create_tilda_article(title, content_html, image_url, author="Bot", seo_title=None):
    """Тильда postadd"""
    if not all([TILDA_PUBLIC_KEY, TILDA_SECRET_KEY, TILDA_PROJECT_ID]):
        return {"error": "Tilda keys missing"}
        
    url = f"https://api.tildacdn.info/v1/postadd?publickey={TILDA_PUBLIC_KEY}&secretkey={TILDA_SECRET_KEY}"
    payload = {
        "projectid": TILDA_PROJECT_ID,
        "title": title,
        "content": content_html,
        "img": image_url,
        "author": author,
        "published": "1"
    }
    if seo_title:
        payload["seo_title"] = seo_title
        
    resp = requests.post(url, json=payload)
    print(f"[TILDA] {resp.status_code}: {resp.text[:200]}")
    return resp.json()

@app.route('/post-with-binary', methods=['POST'])
def post_with_binary():
    """Make.com multipart → Cloudinary → Tilda"""
    
    # Динамические данные из Make.com
    title = request.form.get('title', 'Test Post')
    content_html = request.form.get('content_html', '<h1>Test</h1>')
    author = request.form.get('author', 'Decorewood Bot')
    seo_title = request.form.get('seo_title')
    
    print(f"📝 Title: {title[:50]}...")
    
    # Поиск файла (любое имя из Make.com)
    image_file = None
    for uploaded_file in request.files.values():
        if uploaded_file and uploaded_file.filename:
            image_file = uploaded_file
            print(f"📁 File: {uploaded_file.filename} ({len(uploaded_file.read())} bytes)")
            uploaded_file.seek(0)  # Reset для чтения
            break
    
    if not image_file:
        print("Files keys:", list(request.files.keys()))
        return jsonify({"error": "No image file found"}), 400
    
    image_bytes = image_file.read()
    print(f"📏 Final size: {len(image_bytes)} bytes")
    
    try:
        # Cloudinary оптимизация
        cloudinary_url = upload_to_cloudinary(image_bytes, public_id=f"tilda-{int(datetime.now().timestamp())}")
        
        # Tilda пост
        result = create_tilda_article(title, content_html, cloudinary_url, author, seo_title)
        
        return jsonify({
            "success": True,
            "tilda_url": result.get("result", {}).get("url", ""),
            "image_cdn": cloudinary_url,
            "title_used": title
        })
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "🚀 Ready!",
        "cloudinary": bool(os.getenv("CLOUDINARY_CLOUD_NAME")),
        "tilda_keys": all([TILDA_PUBLIC_KEY, TILDA_SECRET_KEY, TILDA_PROJECT_ID])
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


