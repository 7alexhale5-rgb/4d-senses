#!/usr/bin/env python3
"""
watch-video.py — Agent Luis's 3D Video Perception Engine
Downloads, transcribes, diarizes, extracts frames, and analyzes any video URL.
ONE COMMAND. ALL SENSES.

Usage:
    python3 ~/.claude/scripts/watch-video.py <URL> [--depth shallow|normal|deep]

Depth levels:
    shallow  — transcript + 5 frames (fastest, ~10s)
    normal   — transcript + diarization + 10 frames + scene detection (default, ~30s)
    deep     — transcript + diarization + 25 frames + emotion + face detection (~60s)

Output: /tmp/video-intelligence/<video_id>/
    transcript.txt       — full transcript with timestamps
    transcript.json      — structured segments
    diarization.json     — who said what (if multi-speaker)
    frames/              — extracted key frames
    analysis.json        — scene descriptions, faces detected
    report.md            — human-readable full report
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Config ──────────────────────────────────────────────
OUTPUT_BASE = Path("/tmp/video-intelligence")
GROQ_ENV = Path.home() / ".claude/secrets/groq.env"
HUME_ENV = Path.home() / ".claude/secrets/hume.env"


def load_env(env_file):
    """Load environment variables from a file."""
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")


def get_video_id(url):
    """Generate a short ID from URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def download_video(url, output_dir):
    """Download video with yt-dlp."""
    print("[1/6] DOWNLOADING video...")
    video_path = output_dir / "video.mp4"
    if video_path.exists():
        print("      (cached)")
        return video_path

    cmd = [
        "yt-dlp",
        "-o", str(video_path),
        "--merge-output-format", "mp4",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if not video_path.exists():
        # yt-dlp sometimes adds format suffix
        for f in output_dir.glob("video.*"):
            if f.suffix in (".mp4", ".mkv", ".webm"):
                f.rename(video_path)
                break

    if video_path.exists():
        print(f"      Downloaded: {video_path.stat().st_size / 1024 / 1024:.1f}MB")
    else:
        print(f"      ERROR: Download failed")
        print(f"      {result.stderr[-500:]}")
        sys.exit(1)

    return video_path


def get_metadata(video_path):
    """Extract video metadata with ffprobe."""
    print("[2/6] READING metadata...")
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    meta = {
        "duration": float(data["format"].get("duration", 0)),
        "size_mb": float(data["format"].get("size", 0)) / 1024 / 1024,
    }
    for stream in data.get("streams", []):
        if stream["codec_type"] == "video":
            meta["width"] = stream.get("width")
            meta["height"] = stream.get("height")
            meta["fps"] = stream.get("r_frame_rate", "?")
            meta["codec"] = stream.get("codec_name")
        elif stream["codec_type"] == "audio":
            meta["audio_codec"] = stream.get("codec_name")
            meta["sample_rate"] = stream.get("sample_rate")

    print(f"      {meta['duration']:.1f}s | {meta.get('width','?')}x{meta.get('height','?')} | {meta.get('fps','?')} fps")
    return meta


def transcribe(video_path, output_dir):
    """Transcribe with Groq Whisper (fast + free)."""
    print("[3/6] HEARING (Groq Whisper transcription)...")
    # Try loading from env file first, then fall back to env vars
    load_env(GROQ_ENV)
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        print("      WARNING: No GROQ_API_KEY. Trying groq-transcribe CLI...")
        return transcribe_cli(video_path, output_dir)

    # Extract audio
    audio_path = output_dir / "audio.wav"
    if not audio_path.exists():
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(audio_path)
        ], capture_output=True, timeout=60)

    # Check file size — Groq limit is 25MB
    audio_size = audio_path.stat().st_size / 1024 / 1024
    if audio_size > 25:
        print(f"      Audio too large ({audio_size:.1f}MB). Compressing...")
        compressed = output_dir / "audio_compressed.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(audio_path),
            "-codec:a", "libmp3lame", "-b:a", "64k",
            str(compressed)
        ], capture_output=True, timeout=60)
        audio_path = compressed

    # Call Groq API via curl (reliable multipart handling)
    try:
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "https://api.groq.com/openai/v1/audio/transcriptions",
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: multipart/form-data",
            "-F", "model=whisper-large-v3",
            "-F", f"file=@{audio_path};type=audio/wav",
            "-F", "response_format=verbose_json",
            "-F", "timestamp_granularities[]=word",
            "-F", "timestamp_granularities[]=segment",
        ], capture_output=True, text=True, timeout=120)
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"      Groq error: {e}. Falling back to CLI.")
        return transcribe_cli(video_path, output_dir)

    # Save outputs
    transcript_text = data.get("text", "")
    segments = data.get("segments", [])
    words = data.get("words", [])

    (output_dir / "transcript.txt").write_text(transcript_text)
    (output_dir / "transcript.json").write_text(json.dumps(segments, indent=2))

    # North Star: word-level timestamps for surgical editing precision
    if words:
        (output_dir / "word_timestamps.json").write_text(json.dumps(words, indent=2))
        print(f"      {len(words)} word timestamps saved")

    word_count = len(transcript_text.split())
    print(f"      {word_count} words | {len(segments)} segments | {len(words)} word timestamps")
    return {"text": transcript_text, "segments": segments, "words": words}


def transcribe_cli(video_path, output_dir):
    """Fallback: use groq-transcribe CLI or curl."""
    audio_path = output_dir / "audio.wav"
    if not audio_path.exists():
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(audio_path)
        ], capture_output=True, timeout=60)

    # Try groq-transcribe script directly
    groq_script = Path.home() / ".claude/skills/_youtube-execution/groq_transcribe.py"
    if groq_script.exists():
        result = subprocess.run(
            ["python3", str(groq_script), str(video_path)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            (output_dir / "transcript.txt").write_text(result.stdout)
            return {"text": result.stdout, "segments": []}

    print("      All transcription methods failed.")
    return {"text": "[transcription failed]", "segments": []}


def diarize(video_path, output_dir):
    """Speaker diarization with pyannote (WHO said what)."""
    print("[4/6] IDENTIFYING speakers (pyannote diarization)...")
    try:
        # Use the CLI script if available
        diarize_script = Path.home() / ".claude/scripts/diarize-audio.py"
        if diarize_script.exists():
            audio_path = output_dir / "audio.wav"
            if not audio_path.exists():
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    str(audio_path)
                ], capture_output=True, timeout=60)

            result = subprocess.run(
                ["python3", str(diarize_script), str(audio_path)],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode == 0:
                (output_dir / "diarization.txt").write_text(result.stdout)
                print(f"      Speaker segments saved")
                return result.stdout
            else:
                print(f"      Diarization failed: {result.stderr[:200]}")
                return None
        else:
            print("      diarize-audio.py not found. Skipping.")
            return None
    except Exception as e:
        print(f"      Diarization error: {e}")
        return None


def extract_frames(video_path, output_dir, num_frames=10, duration=None):
    """Extract evenly-spaced key frames."""
    print(f"[5/6] SEEING (extracting {num_frames} key frames)...")
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    if duration and duration > 0:
        interval = max(1, duration / num_frames)
    else:
        interval = 3  # fallback: every 3 seconds

    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"fps=1/{interval:.1f}",
        "-q:v", "2",
        "-frames:v", str(num_frames),
        str(frames_dir / "frame_%03d.jpg")
    ], capture_output=True, timeout=60)

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    print(f"      Extracted {len(frames)} frames")
    return frames


def detect_faces(frames, output_dir):
    """Face detection using facenet-pytorch."""
    print("      Running face detection...")
    try:
        from facenet_pytorch import MTCNN
        from PIL import Image

        mtcnn = MTCNN(keep_all=True)
        face_data = []

        for frame_path in frames:
            img = Image.open(frame_path)
            boxes, probs = mtcnn.detect(img)
            if boxes is not None:
                face_data.append({
                    "frame": frame_path.name,
                    "faces": len(boxes),
                    "confidences": [float(p) for p in probs]
                })

        (output_dir / "faces.json").write_text(json.dumps(face_data, indent=2))
        total_faces = sum(d["faces"] for d in face_data)
        print(f"      {total_faces} face detections across {len(face_data)} frames")
        return face_data
    except ImportError:
        print("      facenet-pytorch not available. Skipping face detection.")
        return []
    except Exception as e:
        print(f"      Face detection error: {e}")
        return []


def gemini_native_perception(video_path, output_dir):
    """Tier 1: Gemini 2.5 native video understanding — sees + hears simultaneously."""
    print("[GEMINI] NATIVE VIDEO PERCEPTION (Tier 1)...")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("      No GEMINI_API_KEY or GOOGLE_API_KEY. Falling back to manual pipeline.")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Upload video
        print("      Uploading to Gemini...")
        video_file = genai.upload_file(path=str(video_path))
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name != "ACTIVE":
            print(f"      Upload failed: {video_file.state.name}")
            return None

        print("      Analyzing with Gemini 2.5 Flash...")
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        response = model.generate_content(
            [video_file, """Watch this entire video and report in markdown:

## Visual Scene
Describe setting, person(s), appearance, clothing, background, lighting, camera angle.

## On-Screen Text
Read ALL text overlays, captions, titles, graphics that appear.

## Transcript
Full verbatim transcript of everything said.

## Emotional Energy
Rate speaker energy (1-10). Describe tone, pace, confidence, emotion shifts.

## Content Analysis
Core message, thesis, target audience.

## Viral Elements
Hook analysis, pacing, call to action, what makes it engaging.

## Production
Shot type, editing style, subtitle/caption style, visual effects.

Be specific. Include timestamps where relevant."""],
            generation_config=genai.types.GenerationConfig(max_output_tokens=4096),
        )

        gemini_report = response.text
        (output_dir / "gemini_perception.md").write_text(gemini_report)
        print(f"      Gemini perception complete ({len(gemini_report)} chars)")

        # Cleanup uploaded file
        try:
            genai.delete_file(video_file.name)
        except Exception:
            pass

        return gemini_report
    except ImportError:
        print("      google-generativeai not installed. Falling back.")
        return None
    except Exception as e:
        print(f"      Gemini error: {e}. Falling back to manual pipeline.")
        return None


def generate_report(url, meta, transcript, diarization, frames, faces, output_dir, gemini_perception=None):
    """Generate human-readable report."""
    print("[6/6] GENERATING report...")

    report = f"""# Video Intelligence Report
**URL:** {url}
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Metadata
- **Duration:** {meta['duration']:.1f}s ({meta['duration']/60:.1f} min)
- **Resolution:** {meta.get('width','?')}x{meta.get('height','?')}
- **FPS:** {meta.get('fps','?')}
- **Size:** {meta.get('size_mb',0):.1f}MB

## Transcript
{transcript.get('text', '[no transcript]')}

## Timestamped Segments
"""
    for seg in transcript.get("segments", []):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "")
        report += f"- [{start:.1f}s - {end:.1f}s] {text}\n"

    if diarization:
        report += f"\n## Speaker Diarization\n{diarization}\n"

    if faces:
        report += "\n## Face Detection\n"
        for f in faces:
            report += f"- {f['frame']}: {f['faces']} face(s)\n"

    if gemini_perception:
        report += f"\n## Gemini Native Perception (Tier 1 — Full 3D Vision)\n{gemini_perception}\n"

    report += f"\n## Frames Extracted\n{len(frames)} frames saved to `{output_dir}/frames/`\n"
    report += "\n---\n*Generated by Agent Luis 3D Vision Engine (Gemini Tier 1 + Manual Fallback)*\n"

    report_path = output_dir / "report.md"
    report_path.write_text(report)
    print(f"      Report: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Agent Luis 3D Video Perception Engine")
    parser.add_argument("url", help="Video URL (YouTube, Instagram, TikTok, Twitter, etc.)")
    parser.add_argument("--depth", choices=["shallow", "normal", "deep"], default="normal",
                        help="Analysis depth (default: normal)")
    parser.add_argument("--no-diarize", action="store_true", help="Skip speaker diarization")
    parser.add_argument("--no-faces", action="store_true", help="Skip face detection")
    args = parser.parse_args()

    # Setup
    video_id = get_video_id(args.url)
    output_dir = OUTPUT_BASE / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save URL for reference
    (output_dir / "source_url.txt").write_text(args.url)

    print(f"\n{'='*60}")
    print(f"  AGENT LUIS — 3D VIDEO PERCEPTION ENGINE")
    print(f"  Depth: {args.depth} | ID: {video_id}")
    print(f"{'='*60}\n")

    # Depth settings
    depth_config = {
        "shallow": {"frames": 5, "diarize": False, "faces": False},
        "normal": {"frames": 10, "diarize": True, "faces": False},
        "deep": {"frames": 25, "diarize": True, "faces": True},
    }
    config = depth_config[args.depth]

    # Execute pipeline
    start = time.time()

    video_path = download_video(args.url, output_dir)
    meta = get_metadata(video_path)

    # Tier 1: Gemini native perception (sees + hears in one pass)
    gemini_perception = gemini_native_perception(video_path, output_dir)

    # Tier 2: Manual pipeline (always runs for transcript/frames — needed for downstream tools)
    transcript = transcribe(video_path, output_dir)

    diarization = None
    if config["diarize"] and not args.no_diarize:
        diarization = diarize(video_path, output_dir)

    frames = extract_frames(video_path, output_dir,
                           num_frames=config["frames"],
                           duration=meta.get("duration"))

    faces = []
    if config["faces"] and not args.no_faces:
        faces = detect_faces(frames, output_dir)

    report_path = generate_report(args.url, meta, transcript, diarization, frames, faces, output_dir,
                                  gemini_perception=gemini_perception)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  COMPLETE in {elapsed:.1f}s")
    print(f"  Output: {output_dir}")
    print(f"  Report: {report_path}")
    print(f"  Frames: {output_dir}/frames/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
