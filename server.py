"""FastAPI server — wraps the verticals CLI pipeline as a REST API.

Endpoints
---------
POST /api/draft    → research + LLM draft (returns JSON for frontend review)
POST /api/produce  → TTS + b-roll + assemble (returns final .mp4 filename)
GET  /media/{filename} → stream the finished video

Run with:
    uvicorn server:app --reload --port 8000
"""

import json
import shutil
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── verticals internals ────────────────────────────────────────────────────────
from verticals.config import DRAFTS_DIR, MEDIA_DIR
from verticals.draft import generate_draft, generate_draft_from_text
from verticals.lang_detect import detect_language
from verticals.state import PipelineState
from verticals.broll import generate_broll
from verticals.tts import generate_voiceover
from verticals.captions import generate_captions
from verticals.music import select_and_prepare_music
from verticals.log import log
from verticals.assemble import assemble_video
from verticals.niche import (
    load_niche,
    get_voice_config,
    get_caption_config,
    get_music_config,
)

# ── app setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Verticals API", version="1.0.0")

from verticals.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure dirs exist before mounting
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

# Serve finished videos directly
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


# ── request / response models ─────────────────────────────────────────────────

class DraftRequest(BaseModel):
    niche: str = "general"
    llm_provider: str | None = "groq"          # claude / gemini / openai / ollama / groq
    image_provider: str | None = "gemini"    # stored in draft for /produce
    tts_provider: str | None = "elevenlabs"      # stored in draft for /produce
    input_mode: str = "topic"                # "topic" | "direct_text" | "url"
    content: str                              # the topic string OR raw script text OR url
    target_words: str = "180-200"             # word count range for LLM script
    uploaded_images: list[str] = []           # base64 encoded images from frontend


class ProduceRequest(BaseModel):
    edited_script: str
    edited_broll_prompts: list[str]
    review_images: list[str] = []
    tts_provider: str | None = "elevenlabs"
    image_provider: str | None = "gemini"
    lang: str = "en"
    duration: str = "20-25"


# ── helpers ───────────────────────────────────────────────────────────────────

def _new_job_id() -> str:
    return str(int(time.time()))


def _save_draft(draft: dict, job_id: str) -> Path:
    """Persist draft JSON and return its path."""
    out_path = DRAFTS_DIR / f"{job_id}.json"
    state = PipelineState(draft)
    state.complete_stage("research")
    state.complete_stage("draft")
    state.save(out_path)
    return out_path


# ── cleanup ───────────────────────────────────────────────────────────────────
def _cleanup_old_data(hours: int = 1):
    """Delete old files and folders in MEDIA_DIR to save disk space."""
    if not MEDIA_DIR.exists():
        return
    now = time.time()
    for item in MEDIA_DIR.iterdir():
        try:
            if item.is_dir() and item.name.startswith("work_"):
                if (now - item.stat().st_mtime) > (hours * 3600):
                    shutil.rmtree(item, ignore_errors=True)
            elif item.is_file() and item.suffix in [".mp4", ".srt"]:
                if (now - item.stat().st_mtime) > (hours * 3600):
                    item.unlink(missing_ok=True)
        except Exception as e:
            print(f"Cleanup error on {item}: {e}")

# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    try:
        from verticals.config import settings
        _ = settings.GEMINI_API_KEY
        return {"status": "ok", "timestamp": time.time(), "keys_valid": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/draft")
def api_draft(req: DraftRequest) -> dict:
    """
    Generate a draft (script + b-roll prompts).

    - input_mode="topic"       → DuckDuckGo research + LLM
    - input_mode="direct_text" → bypass research, feed text straight to LLM
    - input_mode="url"         → scrape article text and images, feed text to LLM
    """
    _cleanup_old_data(hours=1)
    
    try:
        if req.input_mode == "direct_text":
            # Detect language from user-provided text
            lang = detect_language(req.content)
            print(f"Detected language: {lang}")

            draft = generate_draft_from_text(
                text=req.content,
                niche=req.niche,
                provider=req.llm_provider,
                lang=lang,
                target_words=req.target_words,
            )
            draft["lang"] = lang

        elif req.input_mode == "url":
            from verticals.scrape import scrape_url
            scrape_data = scrape_url(req.content)
            
            # --- Print stats to terminal ---
            print("\n----- SCRAPE STATS -----")
            word_count = len(scrape_data["text"].split())
            image_count = len(scrape_data["images"])
            print(f"Words extracted: {word_count}")
            print(f"Images extracted: {image_count}")

            # Detect language from scraped text
            lang = detect_language(scrape_data["text"])
            print(f"Detected language: {lang}")
            print("------------------------\n")

            draft = generate_draft_from_text(
                text=scrape_data["text"],
                niche=req.niche,
                provider=req.llm_provider,
                lang=lang,
                target_words=req.target_words,
            )
            # Store raw urls, we will process them right below
            _scrape_images_raw = scrape_data["images"]
            draft["lang"] = lang

        else:
            # Topic mode — default to English
            draft = generate_draft(
                news=req.content,
                niche=req.niche,
                provider=req.llm_provider,
                target_words=req.target_words,
            )
            draft["lang"] = "en"

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    job_id = _new_job_id()
    work_dir = MEDIA_DIR / f"work_{job_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Process scraped images if any
    valid_scraped_urls = []
    if req.input_mode == "url" and "_scrape_images_raw" in locals():
        from verticals.scrape import download_image
        import uuid
        from PIL import Image, ImageOps
        seen_sizes = set()
        
        for i, img_url in enumerate(_scrape_images_raw):
            if img_url.startswith("data:"):
                continue
            try:
                out_path = work_dir / f"scraped_{i}_{uuid.uuid4().hex[:6]}.jpg"
                download_image(img_url, out_path)

                img = Image.open(out_path).convert("RGB")
                if img.width < 100 or img.height < 100:
                    raise ValueError(f"Image too small: {img.width}x{img.height}")

                file_size = out_path.stat().st_size
                if file_size in seen_sizes:
                    continue
                seen_sizes.add(file_size)

                padded = ImageOps.pad(img, (1920, 1080), color=(0, 0, 0))
                padded.save(out_path)
                
                valid_scraped_urls.append(f"/media/work_{job_id}/{out_path.name}")
            except Exception as e:
                print(f"Failed to use scraped image {img_url[:60]}... : {e}")

    # Handle uploaded images if any
    uploaded_urls = []
    if req.uploaded_images:
        import base64
        import uuid
        from PIL import Image, ImageOps 
        for i, b64_str in enumerate(req.uploaded_images):
            try:
                if "," in b64_str:
                    b64_str = b64_str.split(",")[1]
                data = base64.b64decode(b64_str)
                path = work_dir / f"uploaded_{i}_{uuid.uuid4().hex[:6]}.jpg"
                path.write_bytes(data)
                
                # Pre-pad to master resolution
                img = Image.open(path).convert("RGB")
                padded = ImageOps.pad(img, (1920, 1080), color=(0, 0, 0))
                padded.save(path)

                uploaded_urls.append(f"/media/work_{job_id}/{path.name}")
            except Exception as e:
                print(f"Failed to save uploaded image {i}: {e}")

    draft["job_id"] = job_id
    draft["scraped_images"] = valid_scraped_urls if "_scrape_images_raw" in locals() else []
    draft["uploaded_images"] = uploaded_urls
    draft["tts_provider"] = req.tts_provider
    draft["image_provider"] = req.image_provider

    _save_draft(draft, job_id)
    return {
        "status": "success",
        "data": {
            "script": draft.get("script", ""),
            "broll_prompts": draft.get("broll_prompts", []),
            "scraped_images": draft.get("scraped_images", []),
            "uploaded_images": draft.get("uploaded_images", []),
            "lang": draft.get("lang", "en"),
            "job_id": job_id
        }
    }


def process_video_task(req: ProduceRequest, job_id: str, lang: str, draft: dict):
    tts_provider = req.tts_provider or "sarvam"
    niche_name = "general"
    MASTER_W, MASTER_H = 1920, 1080
    status_file = MEDIA_DIR / f"status_{job_id}.json"
    
    try:
        profile = load_niche(niche_name)
        work_dir = MEDIA_DIR / f"work_{job_id}_{lang}"
        work_dir.mkdir(parents=True, exist_ok=True)
        script = draft.get("script", "")

        from verticals.scrape import download_image
        import uuid
        from PIL import Image, ImageOps

        IMAGE_COUNTS = {'20-25': 3, '45-50': 4, '60': 5, '90': 5, '120': 6}
        target_count = IMAGE_COUNTS.get(req.duration, 3)
        log(f"   - Building b-roll: target {target_count} frames (duration: {req.duration})")

        frames = []
        for i, img_data in enumerate(req.review_images):
            if len(frames) >= target_count:
                break
                
            try:
                new_path = work_dir / f"review_{i}_{uuid.uuid4().hex[:6]}.jpg"
                if img_data.startswith("data:"):
                    import base64
                    b64_str = img_data.split(",")[1] if "," in img_data else img_data
                    new_path.write_bytes(base64.b64decode(b64_str))
                    img = Image.open(new_path).convert("RGB")
                    padded = ImageOps.pad(img, (MASTER_W, MASTER_H), color=(0, 0, 0))
                    padded.save(new_path)
                    frames.append(new_path)
                elif img_data.startswith("/media/"):
                    rel_path = img_data.replace("/media/", "")
                    local_path = MEDIA_DIR / rel_path
                    if local_path.exists():
                        shutil.copy(local_path, new_path)
                        frames.append(new_path)
                else:
                    download_image(img_data, new_path)
                    img = Image.open(new_path).convert("RGB")
                    padded = ImageOps.pad(img, (MASTER_W, MASTER_H), color=(0, 0, 0))
                    padded.save(new_path)
                    frames.append(new_path)
            except Exception as e:
                print(f"Failed to process review image {img_data[:60]}... : {e}")

        shortfall = target_count - len(frames)
        if shortfall > 0:
            prompts = draft.get("broll_prompts") or []
            while len(prompts) < target_count:
                prompts.append("Cinematic landscape related to the topic")
            target_prompts = prompts[len(frames):target_count]
            ai_frames = generate_broll(target_prompts, work_dir)
            for af in ai_frames:
                img = Image.open(af).convert("RGB")
                padded = ImageOps.pad(img, (MASTER_W, MASTER_H), color=(0, 0, 0))
                padded.save(af)
            frames.extend(ai_frames)

        frames = frames[:target_count]
        print(f"Final frame count: {len(frames)}")

        voice_config = get_voice_config(profile, provider=tts_provider, lang=lang)
        vo_path = generate_voiceover(script, work_dir, lang, provider=tts_provider, voice_config=voice_config)

        caption_config = get_caption_config(profile)
        captions_result = generate_captions(vo_path, work_dir, lang, highlight_color=caption_config.get("highlight_color", "#FFFF00"), words_per_group=caption_config.get("words_per_group", 4))

        music_config = get_music_config(profile)
        music_result = select_and_prepare_music(vo_path, work_dir, duck_speech=music_config.get("duck_volume_speech", 0.12), duck_gap=music_config.get("duck_volume_gap", 0.25))

        video_path = assemble_video(frames=frames, voiceover=vo_path, out_dir=work_dir, job_id=job_id, lang=lang, ass_path=captions_result.get("ass_path"), music_path=music_result.get("track_path"), duck_filter=music_result.get("duck_filter"))

        srt_src = captions_result.get("srt_path", "")
        if srt_src and Path(srt_src).exists():
            final_srt = MEDIA_DIR / f"verticals_{job_id}_{lang}.srt"
            shutil.copy(srt_src, final_srt)

        filename = video_path.name
        status_file.write_text(json.dumps({"status": "success", "video_url": f"/media/{filename}"}))

    except Exception as exc:
        status_file.write_text(json.dumps({"status": "error", "error": str(exc)}))
        print(f"Background task failed: {exc}")


@app.post("/api/produce")
def api_produce(req: ProduceRequest, background_tasks: BackgroundTasks) -> dict:
    """
    Triggers background TTS → b-roll → captions → music → assemble.
    Returns { "status": "processing", "job_id": "..." }
    """
    lang = req.lang
    draft = {
        "script": req.edited_script,
        "broll_prompts": req.edited_broll_prompts,
    }
    job_id = _new_job_id()
    
    background_tasks.add_task(process_video_task, req, job_id, lang, draft)
    
    return {
        "status": "processing",
        "job_id": job_id
    }

@app.get("/api/status/{job_id}")
def api_status(job_id: str) -> dict:
    """Check the status of a background produce task."""
    status_file = MEDIA_DIR / f"status_{job_id}.json"
    if not status_file.exists():
        return {"status": "processing"}
    return json.loads(status_file.read_text())

# ── serve frontend (production) ───────────────────────────────────────────────
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
