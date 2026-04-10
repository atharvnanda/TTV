from pathlib import Path
from .config import MEDIA_DIR, run_cmd, get_best_h264_encoder, VIDEO_WIDTH, VIDEO_HEIGHT
from .log import log


def get_audio_duration(path: Path) -> float:
    """Get duration of an audio file in seconds."""
    r = run_cmd(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture=True,
    )
    return float(r.stdout.strip())


def animate_frame_hw(
    img_path: Path, 
    out_path: Path, 
    duration: float, 
    effect: str, 
    encoder: str,
    w: int, 
    h: int
):
    """Animate a single frame using hardware acceleration."""
    fps = 30
    frames = int(duration * fps)
    encoder_opts = ["-preset", "ultrafast"] if encoder == "libx264" else []

    if effect == "zoom_in":
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.12-0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={w}x{h}:fps={fps},format=yuv420p"
        )
    elif effect == "pan_right":
        vf = (
            f"scale={int(w * 1.15)}:{int(h * 1.15)},"
            f"zoompan=z=1.15:x='0.15*iw*on/{frames}':y='ih*0.075'"
            f":d={frames}:s={w}x{h}:fps={fps},format=yuv420p"
        )
    else:  # zoom_out
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.0+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={w}x{h}:fps={fps},format=yuv420p"
        )

    run_cmd([
        "ffmpeg", "-loop", "1", "-i", str(img_path),
        "-vf", vf, "-t", str(duration), "-r", str(fps),
        "-c:v", encoder
    ] + encoder_opts + [
        str(out_path), "-y", "-loglevel", "quiet"
    ])


def assemble_video(
    frames: list[Path],
    voiceover: Path,
    out_dir: Path,
    job_id: str,
    lang: str = "en",
    ass_path: str | None = None,
    music_path: str | None = None,
    duck_filter: str | None = None,
) -> Path:
    """Assemble final video using a stable and fast Turbo-Hybrid approach."""
    log("Starting Turbo-Hybrid hardware-accelerated assembly...")
    
    duration = get_audio_duration(voiceover)
    per_frame = duration / len(frames)
    encoder = get_best_h264_encoder()
    w, h = VIDEO_WIDTH, VIDEO_HEIGHT

    # Phase 1: Animate each frame into a mini-segment
    log(f"   - Animating {len(frames)} frames via {encoder}...")
    effects = ["zoom_in", "pan_right", "zoom_out"]
    segments = []
    for i, frame in enumerate(frames):
        seg_path = out_dir / f"seg_{i}.mp4"
        animate_frame_hw(
            frame, seg_path, per_frame + 0.1, 
            effects[i % len(effects)], encoder, w, h
        )
        segments.append(seg_path)

    # Phase 2: Instant Join (Concat Demuxer)
    log("   - Merging segments...")
    concat_txt = out_dir / "concat_list.txt"
    # Use forward slashes and escaped quotes for FFmpeg on Windows
    def _esc(p):
        return str(p).replace("\\", "/")
    
    txt_content = "\n".join([f"file '{_esc(p)}'" for p in segments])
    concat_txt.write_text(txt_content)

    merged_video = out_dir / "merged_no_audio.mp4"
    run_cmd([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c", "copy", str(merged_video), "-y", "-loglevel", "quiet"
    ])

    # Phase 3: Final Master Pass (Audio + Captions)
    log(f"   - Mastering final video via {encoder}...")
    out_path = MEDIA_DIR / f"verticals_{job_id}_{lang}.mp4"
    
    # Inputs: Merged Video [0:v], Voiceover [1:a], Music [2:a]
    cmd = ["ffmpeg", "-i", str(merged_video), "-i", str(voiceover)]
    
    # Filter setup
    vf_parts = []
    if ass_path and Path(ass_path).exists():
        import sys
        # Note: In -vf (non-complex), typical Windows path escaping works better
        if sys.platform == "win32":
            safe_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
            vf_parts.append(f"ass='{safe_ass}'")
        else:
            escaped_ass = str(ass_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
            vf_parts.append(f"ass={escaped_ass}")

    audio_idx = 1
    if music_path and Path(music_path).exists():
        cmd += ["-i", str(music_path)]
        mu_idx = 2
        # Ducking logic
        a_filter = f"[{mu_idx}:a]aloop=loop=-1:size=2e+09,atrim=0:{duration}"
        if duck_filter:
            a_filter += f",{duck_filter}"
        a_filter += "[music];[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        cmd += ["-filter_complex", a_filter, "-map", "0:v", "-map", "[aout]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]

    if vf_parts:
        cmd += ["-vf", ",".join(vf_parts)]

    # Final Encoding Options
    encoder_opts = ["-preset", "ultrafast"] if encoder == "libx264" else []
    cmd += [
        "-c:v", encoder
    ] + encoder_opts + [
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-pix_fmt", "yuv420p",
        str(out_path), "-y", "-loglevel", "quiet"
    ]

    run_cmd(cmd)
    log(f"Turbo-Hybrid assembly complete: {out_path.name}")
    return out_path
