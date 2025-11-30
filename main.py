from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

app = FastAPI()

# CORS – yahan apna Vercel URL dal sakta hai, abhi * rehne de
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- common yt-dlp options (no download, sirf info) ----
YDL_OPTS = {
    "quiet": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "geo_bypass": True,
}


def extract_formats(info):
    audio = []
    video = []
    for f in info.get("formats", []):
        # audio only
        if f.get("vcodec") == "none":
            audio.append({
                "url": f.get("url"),
                "ext": f.get("ext"),
                "abr": f.get("abr"),
                "format_id": f.get("format_id"),
                "format": f.get("format_note") or f.get("format"),
                "type": "audio",
            })
        # video (with or without audio)
        else:
            video.append({
                "url": f.get("url"),
                "ext": f.get("ext"),
                "height": f.get("height"),
                "fps": f.get("fps"),
                "format_id": f.get("format_id"),
                "format": f.get("format_note") or f.get("format"),
                "type": "video",
            })
    return audio, video


@app.get("/info")
async def info(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL missing")

    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {e}")

    audio, video = extract_formats(info)

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "audio": audio,
        "video": video,
    }


@app.get("/download")
async def download(url: str, format_id: str | None = None):
    """
    Optional endpoint: agar tu chaahe to redirect kara sakta hai
    /download?url=<youtube>&format_id=22
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL missing")

    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {e}")

    target = None

    if format_id:
        for f in info.get("formats", []):
            if f.get("format_id") == format_id:
                target = f
                break
    else:
        # default: best video+audio
        target = info.get("formats", [])[-1]

    if not target or not target.get("url"):
        raise HTTPException(status_code=404, detail="Format not found")

    # FastAPI redirect
    from fastapi.responses import RedirectResponse
    return RedirectResponse(target["url"], status_code=302)
