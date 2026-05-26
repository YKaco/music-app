from flask import Flask, render_template, request, send_from_directory, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name.strip()[:200]


# --------------------------
# ① URL情報取得（タイトル・秒数）
# --------------------------
@app.route("/preview", methods=["POST"])
def preview():
    try:
        url = request.json.get("url", "").strip()
        if not url:
            return jsonify({"error": "URLが空です"}), 400

        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title":    info.get("title", "不明"),
            "duration": info.get("duration", 0),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------
# ② ダウンロード（時間指定OK）
# --------------------------
@app.route("/download", methods=["POST"])
def download():
    try:
        data  = request.json
        url   = data.get("url", "").strip()
        start = int(data.get("start", 0))
        end   = data.get("end")
        end   = int(end) if end else None

        if not url:
            return jsonify({"error": "URLが空です"}), 400

        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info      = ydl.extract_info(url, download=False)
            raw_title = info.get("title", "output")

        safe_title = sanitize_filename(raw_title)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{DOWNLOAD_FOLDER}/{safe_title}.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        }

        if end is not None:
            ydl_opts["download_sections"] = [f"*{start}-{end}"]
        elif start > 0:
            ydl_opts["download_sections"] = [f"*{start}-"]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({"filename": f"{safe_title}.mp3"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------
# ファイル取得
# --------------------------
@app.route("/file/<path:filename>")
def file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
