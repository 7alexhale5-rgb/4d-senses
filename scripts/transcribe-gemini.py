#!/usr/bin/env python3
"""
transcribe-gemini.py — Fast audio/video transcription via Gemini 2.5 Flash
No chunking. No rate limits. No waiting. One API call per file.

Usage:
    python3 transcribe-gemini.py <audio-or-video-file> [--output path.md]
    python3 transcribe-gemini.py --batch <dir-of-files> [--output-dir path/]

Supports: .mp3, .m4a, .wav, .flac, .ogg, .mp4, .ts, .mov, .webm, .mkv
For video files, extracts audio first via ffmpeg.

Speed: ~60s for 1 hour of audio. ~2 min for 3 hours.
Cost: Free tier handles files up to 2GB / 6 hours.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import warnings

warnings.filterwarnings('ignore')

GEMINI_KEY_FILE = os.path.expanduser('~/.claude/secrets/gemini.env')
VIDEO_EXTS = {'.mp4', '.ts', '.mov', '.webm', '.mkv', '.avi'}
AUDIO_EXTS = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.opus'}


def load_key():
    if not os.path.exists(GEMINI_KEY_FILE):
        print(f'Error: No Gemini key at {GEMINI_KEY_FILE}', file=sys.stderr)
        sys.exit(1)
    with open(GEMINI_KEY_FILE) as f:
        key = f.read().split('=', 1)[1].strip()
    if not key:
        print(f'Error: Empty API key in {GEMINI_KEY_FILE}', file=sys.stderr)
        sys.exit(1)
    return key


def extract_audio(video_path):
    """Extract audio from video to temp mp3."""
    tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
    print(f'  Extracting audio from video...', file=sys.stderr)
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vn', '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1', '-b:a', '48k',
        tmp, '-y'
    ], capture_output=True, check=True)
    return tmp


def transcribe(file_path, client):
    """Transcribe a single audio file via Gemini 2.5 Flash."""
    ext = os.path.splitext(file_path)[1].lower()

    # Extract audio from video if needed
    audio_path = file_path
    tmp_audio = None
    if ext in VIDEO_EXTS:
        tmp_audio = extract_audio(file_path)
        audio_path = tmp_audio

    # Upload to Gemini
    upload = None
    try:
        size_mb = os.path.getsize(audio_path) / 1024 / 1024
        print(f'  Uploading {size_mb:.1f}MB to Gemini...', file=sys.stderr)
        upload = client.files.upload(file=audio_path)

        # Transcribe
        print(f'  Transcribing via Gemini 2.5 Flash...', file=sys.stderr)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                'Transcribe this audio verbatim. Output ONLY the transcript text. '
                'No timestamps, no speaker labels, no commentary, no formatting. '
                'Just the exact spoken words as continuous text paragraphs.',
                upload
            ]
        )
        return response.text
    finally:
        # Always clean up remote upload and local temp file
        if upload:
            try:
                client.files.delete(name=upload.name)
            except Exception:
                pass
        if tmp_audio and os.path.exists(tmp_audio):
            os.unlink(tmp_audio)


def main():
    parser = argparse.ArgumentParser(description='Fast transcription via Gemini 2.5 Flash')
    parser.add_argument('file', nargs='?', help='Audio or video file to transcribe')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--batch', help='Directory of files to transcribe')
    parser.add_argument('--output-dir', help='Output directory for batch mode')
    args = parser.parse_args()

    key = load_key()
    from google import genai
    client = genai.Client(api_key=key)

    if args.batch:
        # Batch mode — parallel via concurrent.futures
        import concurrent.futures
        import time

        out_dir = args.output_dir or os.path.join(args.batch, 'transcripts')
        os.makedirs(out_dir, exist_ok=True)

        files = sorted([
            f for f in os.listdir(args.batch)
            if os.path.splitext(f)[1].lower() in VIDEO_EXTS | AUDIO_EXTS
        ])

        # Filter already-done
        todo = []
        for f in files:
            base = os.path.splitext(f)[0]
            out_path = os.path.join(out_dir, f'{base}.md')
            if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                print(f'  Skipping {f} (already transcribed)', file=sys.stderr)
            else:
                todo.append(f)

        print(f'Transcribing {len(todo)} files in parallel...', file=sys.stderr)
        start = time.time()

        def process_file(f):
            path = os.path.join(args.batch, f)
            base = os.path.splitext(f)[0]
            out_path = os.path.join(out_dir, f'{base}.md')
            try:
                text = transcribe(path, client)
                with open(out_path, 'w') as out:
                    out.write(f'# {base}\n\n---\n\n{text}\n')
                return f, len(text), None
            except Exception as e:
                return f, 0, str(e)

        max_workers = min(len(todo), 3)  # Gemini free tier: 15 RPM
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(process_file, f): f for f in todo}
            for future in concurrent.futures.as_completed(futures):
                f, chars, err = future.result()
                if err:
                    print(f'  [{f}] Error: {err}', file=sys.stderr)
                else:
                    print(f'  [{f}] Done: {chars} chars', file=sys.stderr)

        elapsed = time.time() - start
        print(f'\nDone. {len(todo)} files in {elapsed:.0f}s. Transcripts in {out_dir}', file=sys.stderr)

    elif args.file:
        # Single file mode
        print(f'[{os.path.basename(args.file)}]', file=sys.stderr)
        text = transcribe(args.file, client)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(text)
            print(f'Saved: {args.output} ({len(text)} chars)', file=sys.stderr)
        else:
            print(text)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
