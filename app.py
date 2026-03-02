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
    """Binary → Cloudinary URL"""
    result = cloudinary.uploader.upload(
        image_bytes, 
        folder="tilda_posts",
        public_id=public_id,
        format="auto",
        quality="auto"
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
    title = request.form.get('title', 'Test Post')
    content_html = request.form.get('content_html', '<h1>Test</h1>')
    author = request.form.get('author', 'Bot')
    seo_title = request.form.get('seo_title')
    
    if 'image' not in request.files:
        return jsonify({"error": "Missing image file"}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "Empty image file"}), 400
        
    image_bytes = image_file.read()
    print(f"📏 Image size: {len(image_bytes)} bytes")
    
    try:
        cloudinary_url = upload_to_cloudinary(image_bytes)
        result = create_tilda_article(title, content_html, cloudinary_url, author, seo_title)
        
        return jsonify({
            "success": True,
            "tilda_url": result.get("result", {}).get("url", ""),
            "image_cdn": cloudinary_url
        })
    except Exception as e:
        print(f"ERROR: {e}")
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
