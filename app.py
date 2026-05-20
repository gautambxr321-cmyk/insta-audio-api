from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)
CORS(app)  # Allow requests from any website (your Blogger)

DOWNLOAD_FOLDER = "/tmp/audio"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Auto-delete files after 5 minutes (cleanup)
def delete_file_later(path, delay=300):
    def _delete():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=_delete, daemon=True).start()


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "InstaAudio API is running ✅"})


@app.route("/extract", methods=["POST"])
def extract_audio():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Basic Instagram URL check
    if "instagram.com" not in url:
        return jsonify({"error": "Please provide a valid Instagram URL"}), 400

    file_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
        # Helps avoid Instagram blocks
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "instagram_audio")

        if not os.path.exists(output_path):
            return jsonify({"error": "Audio extraction failed. Reel may be private."}), 500

        # Schedule file deletion after 5 min
        delete_file_later(output_path)

        return jsonify({
            "success": True,
            "title": title,
            "download_url": f"/download/{file_id}",
            "filename": f"{file_id}.mp3"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download/<file_id>", methods=["GET"])
def download_file(file_id):
    path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp3")
    if not os.path.exists(path):
        return jsonify({"error": "File not found or expired"}), 404
    return send_file(path, as_attachment=True, download_name="instagram_audio.mp3")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
