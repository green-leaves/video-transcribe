# Dependencies: pip install openai-whisper
# External binaries required: yt-dlp, claude

import re
import json
import shutil
import subprocess
import sys
from pathlib import Path

import whisper


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def get_video_info(url: str) -> tuple[str, str]:
    print(f"Fetching video info for {url} ...")
    result = subprocess.run(
        ['yt-dlp', '--dump-json', url],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    return info['id'], info['title']


def transcribe(mp3_path: Path, txt_path: Path, model: str) -> None:
    print(f"Transcribing {mp3_path} with whisper model '{model}' ...")
    model_obj = whisper.load_model(model)
    result = model_obj.transcribe(str(mp3_path))
    txt_path.write_text(result['text'])
    print(f"Raw transcript written to {txt_path}")


def format_transcript(txt_path: Path, md_path: Path, prompt_path: Path) -> None:
    print("Formatting transcript with Claude ...")
    system_prompt = prompt_path.read_text()
    transcript = txt_path.read_text()
    message = f"{system_prompt}\n\nRaw transcript:\n\n{transcript}"
    result = subprocess.run(
        ['claude', '-p', message],
        capture_output=True, text=True, check=True
    )
    md_path.write_text(result.stdout)
    print(f"Final markdown written to {md_path}")


def download_audio(url: str, output_path: Path) -> None:
    print(f"Downloading audio to {output_path} ...")
    subprocess.run(
        ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', str(output_path), url],
        check=True
    )


def check_dependencies() -> None:
    for tool in ('yt-dlp', 'claude'):
        if shutil.which(tool) is None:
            print(f"Error: '{tool}' not found on PATH. Please install it.")
            sys.exit(1)


def build_output_paths(output_dir: str, video_id: str, title: str) -> dict:
    slug = f"{video_id}-{slugify(title)}"
    base = Path(output_dir) / slug
    return {
        'mp3': base.with_suffix('.mp3'),
        'txt': base.with_suffix('.txt'),
        'md': base.with_suffix('.md'),
    }
