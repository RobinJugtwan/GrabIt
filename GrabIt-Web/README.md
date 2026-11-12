# 🚀 GrabIt Web — Universal Media Downloader

A full-stack, cloud-ready web application to download video, audio, and media from **1000+ websites** (YouTube, Instagram, TikTok, Twitter/X, Pinterest, Reddit, etc.) with in-browser previews and direct streaming to your browser.

---

## ⚡ Option 1: Run Locally (Zero Setup)

Double-click `start.bat` or run:

```bash
cd C:\Users\robin\Downloads\GrabIt-Web
pip install -r requirements.txt
python main.py
```

Then open your browser to: **`http://localhost:8000`**

---

## 🌐 Option 2: Deploy Free to the Cloud

### Method A: 100% Free on Render.com (Recommended)

1. Create a free account at [Render.com](https://render.com).
2. Create a new GitHub repo and push this `GrabIt-Web` folder to it.
3. On Render, click **New +** → **Web Service**.
4. Connect your GitHub repository.
5. Render will automatically detect the settings:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Click **Deploy Web Service**!
   - You will get a free live URL: `https://grabit-web.onrender.com`

---

### Method B: 100% Free on Hugging Face Spaces (No limits!)

1. Create a free account on [Hugging Face](https://huggingface.co).
2. Click your profile → **New Space**.
3. Name it `grabit-web` and select **Space SDK: Docker** (Blank).
4. Upload all files from this folder (`Dockerfile`, `main.py`, `requirements.txt`, `static/`).
5. Hugging Face will automatically build the container with full FFmpeg and give you a free permanent link:
   - `https://yourusername-grabit-web.hf.space`

---

## 📁 Project Architecture

```
GrabIt-Web/
├── main.py              # FastAPI backend (metadata extraction & file streaming)
├── static/
│   └── index.html       # Full responsive frontend UI with in-browser player & themes
├── requirements.txt     # Python dependencies (fastapi, uvicorn, yt-dlp)
├── Dockerfile           # Multi-platform container configuration (with FFmpeg)
├── Procfile             # Standard PaaS process runner
├── render.yaml          # Render Blueprint deployment definition
└── start.bat            # 1-click Windows local launcher
```
