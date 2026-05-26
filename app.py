from flask import Flask, render_template, request, send_from_directory, jsonify, session, redirect, url_for
import yt_dlp
import os
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name.strip()[:200]


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# --------------------------
# ログイン
# --------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "パスワードが違います"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------
# ① URL情報取得（タイトル・秒数）
# --------------------------
@app.route("/preview", methods=["POST"])
@login_required
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
@login_required
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
@login_required
def file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


@app.route("/")
@login_required
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
