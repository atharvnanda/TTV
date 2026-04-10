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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from verticals.assemble import assemble_video
from verticals.niche import (
    load_niche,
    get_voice_config,
    get_caption_config,
    get_music_config,
)

# ── app setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Verticals API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
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
    llm_provider: str | None = None          # claude / gemini / openai / ollama / groq
    image_provider: str | None = "gemini"    # stored in draft for /produce
    tts_provider: str | None = "sarvam"      # stored in draft for /produce
    input_mode: str = "topic"                # "topic" | "direct_text" | "url"
    content: str                              # the topic string OR raw script text OR url
    target_words: str = "180-200"             # word count range for LLM script


class ProduceRequest(BaseModel):
    edited_script: str
    edited_broll_prompts: list[str]
    scraped_images: list[str] = []
    tts_provider: str | None = "sarvam"
    image_provider: str | None = "gemini"
    lang: str = "en"


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


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/draft")
def api_draft(req: DraftRequest) -> dict:
    """
    Generate a draft (script + b-roll prompts).

    - input_mode="topic"       → DuckDuckGo research + LLM
    - input_mode="direct_text" → bypass research, feed text straight to LLM
    - input_mode="url"         → scrape article text and images, feed text to LLM
    """
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
            draft["scraped_images"] = scrape_data["images"]
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
    draft["job_id"] = job_id
    draft["tts_provider"] = req.tts_provider
    draft["image_provider"] = req.image_provider

    _save_draft(draft, job_id)
    return {
        "status": "success",
        "data": {
            "script": draft.get("script", ""),
            "broll_prompts": draft.get("broll_prompts", []),
            "scraped_images": draft.get("scraped_images", []),
            "lang": draft.get("lang", "en"),
            "job_id": job_id
        }
    }


@app.post("/api/produce")
def api_produce(req: ProduceRequest) -> dict:
    """
    Run TTS → b-roll → captions → music → assemble.

    Accepts the (possibly edited) draft JSON from the frontend.
    Returns { "filename": "verticals_<job_id>_en.mp4", "url": "/media/..." }
    """
    lang = req.lang
    draft = {
        "script": req.edited_script,
        "broll_prompts": req.edited_broll_prompts,
    }
    job_id = _new_job_id()

    # Resolve providers — frontend selection wins over draft defaults
    tts_provider = req.tts_provider or "sarvam"
    niche_name = "general"

    # Fixed landscape master resolution
    MASTER_W, MASTER_H = 1920, 1080

    try:
        profile = load_niche(niche_name)

        work_dir = MEDIA_DIR / f"work_{job_id}_{lang}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Use the script as-is (already in the correct language from /api/draft)
        script = draft.get("script", "")

        # 1 — B-roll images: deterministic hybrid sourcing
        from verticals.scrape import download_image
        import uuid
        from PIL import Image, ImageOps

        # Step 1: Download & validate scraped images (cap at 3 unique ones)
        scraped_images = req.scraped_images
        downloaded_imgs = []
        seen_sizes = set()

        for i, img_url in enumerate(scraped_images):
            if len(downloaded_imgs) >= 3:
                break

            if img_url.startswith("data:"):
                continue

            try:
                out_path = work_dir / f"scraped_{i}_{uuid.uuid4().hex[:6]}.jpg"
                download_image(img_url, out_path)

                # Validate image
                img = Image.open(out_path).convert("RGB")
                if img.width < 100 or img.height < 100:
                    raise ValueError(f"Image too small: {img.width}x{img.height}")

                # Deduplicate by file size (catch OG vs Body duplicates that URL normalization missed)
                file_size = out_path.stat().st_size
                if file_size in seen_sizes:
                    print(f"Skipping duplicate image (same size): {img_url[:60]}...")
                    continue
                seen_sizes.add(file_size)

                # Pad to master resolution (letterbox)
                padded = ImageOps.pad(img, (MASTER_W, MASTER_H), color=(0, 0, 0))
                padded.save(out_path)
                downloaded_imgs.append(out_path)
            except Exception as e:
                print(f"Failed to use scraped image {img_url[:60]}... : {e}")

        # Step 2: Build frames list — scraped images first
        frames = list(downloaded_imgs)

        # Step 3: Fill shortfall with AI-generated images
        shortfall = 3 - len(frames)
        if shortfall > 0:
            prompts = draft.get("broll_prompts") or []
            # Guarantee at least 3 prompts
            while len(prompts) < 3:
                prompts.append("Cinematic landscape related to the topic")

            # Use prompts for the remaining slot positions
            target_prompts = prompts[len(frames):len(frames) + shortfall]

            ai_frames = generate_broll(
                target_prompts,
                work_dir,
            )
            # Pad AI frames to master resolution
            for af in ai_frames:
                img = Image.open(af).convert("RGB")
                padded = ImageOps.pad(img, (MASTER_W, MASTER_H), color=(0, 0, 0))
                padded.save(af)

            frames.extend(ai_frames)

        # Guarantee exactly 3 frames
        frames = frames[:3]
        print(f"Final frame count: {len(frames)} (scraped: {len(downloaded_imgs)}, ai: {len(frames) - len(downloaded_imgs)})")

        # 2 — Voiceover (TTS)
        voice_config = get_voice_config(profile, provider=tts_provider, lang=lang)
        vo_path = generate_voiceover(
            script, work_dir, lang,
            provider=tts_provider,
            voice_config=voice_config,
        )

        # 3 — Captions (Whisper)
        caption_config = get_caption_config(profile)
        captions_result = generate_captions(
            vo_path, work_dir, lang,
            highlight_color=caption_config.get("highlight_color", "#FFFF00"),
            words_per_group=caption_config.get("words_per_group", 4),
        )

        # 4 — Background music
        music_config = get_music_config(profile)
        music_result = select_and_prepare_music(
            vo_path, work_dir,
            duck_speech=music_config.get("duck_volume_speech", 0.12),
            duck_gap=music_config.get("duck_volume_gap", 0.25),
        )

        # 5 — FFmpeg assembly
        video_path = assemble_video(
            frames=frames,
            voiceover=vo_path,
            out_dir=work_dir,
            job_id=job_id,
            lang=lang,
            ass_path=captions_result.get("ass_path"),
            music_path=music_result.get("track_path"),
            duck_filter=music_result.get("duck_filter"),
        )

        # Copy SRT alongside media
        srt_src = captions_result.get("srt_path", "")
        if srt_src and Path(srt_src).exists():
            final_srt = MEDIA_DIR / f"verticals_{job_id}_{lang}.srt"
            shutil.copy(srt_src, final_srt)

        filename = video_path.name
        return {
            "status": "success",
            "video_url": f"http://localhost:8000/media/{filename}"
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
