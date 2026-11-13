import os
import re
import tempfile
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="GrabIt Web API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMP_DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "grabit_downloads")
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)


class InfoRequest(BaseModel):
    url: str


class BatchInfoRequest(BaseModel):
    urls: List[str]


def clean_filename(title: str) -> str:
    """Sanitize title for safe cross-platform filename"""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", title)
    return cleaned.strip()[:100] or "media_file"


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "Unknown"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def extract_media_info(url: str):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb"]
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("Could not extract media info")
        
        # In case of playlist, pick the first video or summary
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        formats_available = []
        if "formats" in info:
            resolutions = set()
            for f in info["formats"]:
                h = f.get("height")
                if h and h not in resolutions and f.get("vcodec") != "none":
                    resolutions.add(h)
                    formats_available.append({
                        "format_id": f.get("format_id"),
                        "resolution": f"{h}p",
                        "height": h,
                        "ext": f.get("ext", "mp4"),
                        "filesize_approx": f.get("filesize") or f.get("filesize_approx")
                    })
            formats_available.sort(key=lambda x: x["height"], reverse=True)

        return {
            "title": info.get("title", "Unknown Title"),
            "uploader": info.get("uploader") or info.get("channel") or info.get("extractor", "Unknown"),
            "duration": format_duration(info.get("duration")),
            "duration_sec": info.get("duration", 0),
            "thumbnail": info.get("thumbnail") or "",
            "platform": info.get("extractor_key") or info.get("extractor") or "Universal",
            "webpage_url": info.get("webpage_url", url),
            "formats": formats_available[:6],
            "direct_url": info.get("url") if info.get("vcodec") != "none" else None
        }


@app.post("/api/info")
async def get_info(req: InfoRequest):
    """Extract metadata, thumbnail, duration, and format options for any URL"""
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        data = await asyncio.to_thread(extract_media_info, req.url)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media: {str(e)}")


@app.post("/api/batch-info")
async def get_batch_info(req: BatchInfoRequest):
    """Extract metadata for multiple URLs simultaneously"""
    results = []
    for url in req.urls[:15]:  # limit to 15 per batch for performance
        try:
            data = await asyncio.to_thread(extract_media_info, url)
            results.append({"url": url, "status": "success", "data": data})
        except Exception as e:
            results.append({"url": url, "status": "error", "error": str(e)})
    return {"results": results}


def remove_file(filepath: str):
    """Background task to remove temporary download file after serving to client"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


@app.get("/api/download")
async def download_media(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="Target video/audio URL"),
    quality: str = Query("best", description="Resolution or format: best, 1080p, 720p, 480p, mp3, m4a"),
    codec: str = Query("mp4", description="mp4, mkv, webm"),
    subs: str = Query("none", description="none, en, auto")
):
    """Downloads media from URL and streams directly as an attachment to client browser"""
    try:
        # Determine format string
        if quality == "mp3":
            ydl_format = "bestaudio/best"
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
            ext = "mp3"
        elif quality == "m4a":
            ydl_format = "bestaudio[ext=m4a]/bestaudio/best"
            postprocessors = []
            ext = "m4a"
        elif quality == "1080p":
            ydl_format = f"bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            postprocessors = []
            ext = codec
        elif quality == "720p":
            ydl_format = f"bestvideo[height<=720]+bestaudio/best[height<=720]"
            postprocessors = []
            ext = codec
        elif quality == "480p":
            ydl_format = f"bestvideo[height<=480]+bestaudio/best[height<=480]"
            postprocessors = []
            ext = codec
        else:
            ydl_format = "bestvideo+bestaudio/best"
            postprocessors = []
            ext = codec

        # Output template in temp folder
        out_template = os.path.join(TEMP_DOWNLOAD_DIR, "%(id)s_%(title).50s.%(ext)s")

        ydl_opts = {
            "format": ydl_format,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": codec if quality not in ["mp3", "m4a"] else None,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android", "mweb"]
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
            }
        }

        if postprocessors:
            ydl_opts["postprocessors"] = postprocessors

        if subs != "none":
            ydl_opts["writesubtitles"] = True
            ydl_opts["subtitleslangs"] = ["en"]
            ydl_opts["writeautomaticsub"] = (subs == "auto")

        # Execute download in thread
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info_dict)
                # If audio conversion changed extension
                if quality == "mp3":
                    base, _ = os.path.splitext(filename)
                    filename = base + ".mp3"
                elif quality not in ["mp3", "m4a"] and codec:
                    base, _ = os.path.splitext(filename)
                    filename = base + f".{codec}"
                return filename, info_dict.get("title", "download")

        filepath, raw_title = await asyncio.to_thread(run_dl)

        if not os.path.exists(filepath):
            # Check if file exists with different extension
            base, _ = os.path.splitext(filepath)
            for f in os.listdir(TEMP_DOWNLOAD_DIR):
                if f.startswith(os.path.basename(base)):
                    filepath = os.path.join(TEMP_DOWNLOAD_DIR, f)
                    break

        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Failed to locate processed download file")

        download_name = f"{clean_filename(raw_title)}.{ext}"

        # Clean up temp file once client browser finishes downloading
        background_tasks.add_task(remove_file, filepath)

        return FileResponse(
            path=filepath,
            filename=download_name,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")


# Serve static folder
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>GrabIt Web Server is Running!</h1><p>static/index.html not found.</p>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 GrabIt Web starting at http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
