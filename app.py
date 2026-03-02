from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import base64

app = Flask(__name__)

# ✅ Тильда ключи
TILDA_PUBLIC_KEY = os.getenv("TILDA_PUBLIC_KEY")
TILDA_SECRET_KEY = os.getenv("TILDA_SECRET_KEY")
TILDA_PROJECT_ID = os.getenv("TILDA_PROJECT_ID")

def download_google_drive(web_content_link):
    print(f"[GD] GET {web_content_link}")
    resp = requests.get(web_content_link)
    print(f"[GD] Status: {resp.status_code}, content-type: {resp.headers.get('Content-Type')}")
    resp.raise_for_status()
    return resp.content

def upload_image_to_tilda_raw(image_bytes, filename="article.png"):
    """Загрузка в Тильду с publickey + secretkey"""
    url = ("https://api.tildacdn.info/v1/uploadimage?"
           f"publickey={TILDA_PUBLIC_KEY}&"
           f"secretkey={TILDA_SECRET_KEY}&"
           f"projectid={TILDA_PROJECT_ID}")
    
    files = {"file": (filename, image_bytes, "image/png")}
    
    print("[TILDA] POST uploadimage...")
    resp = requests.post(url, files=files)
    print(f"[TILDA] Status: {resp.status_code}")
    print(f"[TILDA] Response: {resp.text[:500]}")
    
    try:
        result = resp.json()
        if result.get("status") == "FOUND":
            return result["result"]["url"]
    except:
        pass
    
    return None

def upload_image_to_tilda(image_base64, filename="article.png"):
    image_data = base64.b64decode(image_base64)
    return upload_image_to_tilda_raw(image_data, filename)

def create_tilda_article(title, content_html, image_url):
    url = f"https://api.tildacdn.info/v1/postadd?publickey={TILDA_PUBLIC_KEY}&secretkey={TILDA_SECRET_KEY}"
    
    payload = {
        "projectid": TILDA_PROJECT_ID,
        "title": title,
        "content": content_html,
        "img": image_url,
        "published": "1"
    }
    
    resp = requests.post(url, json=payload)
    print(f"[POSTADD] Status: {resp.status_code}, Response: {resp.text[:300]}")
    return resp.json()

@app.route('/post-to-tilda', methods=['POST'])
def post_article():
    data = request.json
    
    title = data['title']
    content = data['content_html']
    image_url = data.get('image_url')
    
    if image_url and 'drive.google.com' in image_url:
        print("🔗 Google Drive")
        image_bytes = download_google_drive(image_url)
        tilda_image_url = upload_image_to_tilda_raw(image_bytes)
    else:
        print("🖼️ Base64")
        image_b64 = data['image_base64']
        tilda_image_url = upload_image_to_tilda(image_b64)
    
    if not tilda_image_url:
        return jsonify({"error": "❌ Image upload failed", "debug": "Check logs"}), 400
    
    result = create_tilda_article(title, content, tilda_image_url)
    
    return jsonify({
        "success": True,
        "tilda_url": result.get("result", {}).get("url", ""),
        "image_url": tilda_image_url
    })

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "🚀 OK", "keys": bool(TILDA_PUBLIC_KEY)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
