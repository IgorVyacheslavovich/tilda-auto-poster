import cloudinary
import cloudinary.uploader
from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Тильда
TILDA_PUBLIC_KEY = os.getenv("TILDA_PUBLIC_KEY")
TILDA_SECRET_KEY = os.getenv("TILDA_SECRET_KEY")
TILDA_PROJECT_ID = os.getenv("TILDA_PROJECT_ID")

def upload_to_cloudinary(image_bytes, public_id="article"):
    """OpenAI bytes → Cloudinary CDN URL"""
    result = cloudinary.uploader.upload(
        image_bytes, 
        folder="tilda_posts",
        public_id=public_id,
        format="auto",  # webp/avif
        quality="auto"
    )
    return result['secure_url']

@app.route('/post-to-tilda', methods=['POST'])
def post_article():
    data = request.json
    
    title = data['title']
    content = data['content_html']
    image_b64 = data['image_base64']  # Из OpenAI!
    
    # 1. Base64 → Cloudinary
    print("☁️ Uploading to Cloudinary...")
    image_bytes = base64.b64decode(image_b64)
    cloudinary_url = upload_to_cloudinary(image_bytes)
    print(f"☁️ CDN: {cloudinary_url}")
    
    # 2. Cloudinary → Тильда postadd
    result = create_tilda_article(title, content, cloudinary_url)
    
    return jsonify({
        "success": True,
        "tilda_url": result.get("result", {}).get("url", ""),
        "image_cdn": cloudinary_url
    })

def create_tilda_article(title, content_html, image_url):
    """Тильда postadd"""
    url = f"https://api.tildacdn.info/v1/postadd?publickey={TILDA_PUBLIC_KEY}&secretkey={TILDA_SECRET_KEY}"
    payload = {
        "projectid": TILDA_PROJECT_ID,
        "title": title,
        "content": content_html,
        "img": image_url,
        "published": "1"
    }
    resp = requests.post(url, json=payload)
    print(f"[TILDA] postadd: {resp.status_code}")
    return resp.json()

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "🚀 Cloudinary + Tilda ready!"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
