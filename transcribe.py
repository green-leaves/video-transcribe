# Dependencies: pip install openai-whisper
# External binaries required: yt-dlp, claude

import re
import json
import shutil
import subprocess
import sys
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


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
