# Dependencies: pip install -r requirements.txt
# External binary required: claude (Claude Code CLI)

import re
import shutil
import subprocess
import sys
from pathlib import Path

import whisper
import yt_dlp


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def build_output_paths(output_dir: str, video_id: str, title: str) -> dict:
    slug = f"{video_id}-{slugify(title)}"
    base = Path(output_dir) / slug
    return {
        'mp3': base.with_suffix('.mp3'),
        'txt': base.with_suffix('.txt'),
        'md': base.with_suffix('.md'),
    }


def check_dependencies() -> None:
    if shutil.which('claude') is None:
        print("Error: 'claude' not found on PATH. Please install the Claude Code CLI.")
        sys.exit(1)


def get_video_info(url: str) -> tuple[str, str]:
    print(f"Fetching video info for {url} ...")
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return info['id'], info['title']


def download_audio(url: str, output_path: Path) -> None:
    print(f"Downloading audio to {output_path} ...")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'outtmpl': str(output_path.with_suffix('')),
        'quiet': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def transcribe(mp3_path: Path, txt_path: Path, model: str) -> None:
    print(f"Transcribing {mp3_path} with whisper model '{model}' ...")
    model_obj = whisper.load_model(model)
    result = model_obj.transcribe(str(mp3_path), verbose=True, language='en')
    txt_path.write_text(result['text'], encoding='utf-8')
    print(f"Raw transcript written to {txt_path}")


def format_transcript(txt_path: Path, md_path: Path, prompt_path: Path) -> None:
    print("Formatting transcript with Claude ...")
    system_prompt = prompt_path.read_text(encoding='utf-8')
    transcript = txt_path.read_text(encoding='utf-8')
    message = f"{system_prompt}\n\nRaw transcript:\n\n{transcript}"
    result = subprocess.run(
        ['claude', '-p', message],
        capture_output=True, text=True, encoding='utf-8', check=True
    )
    md_path.write_text(result.stdout, encoding='utf-8')
    print(f"Final markdown written to {md_path}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video or local audio file to markdown.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--url', help='YouTube video URL')
    source.add_argument('--file', help='Path to a local audio file (mp3, wav, m4a, ...)')
    parser.add_argument('--output', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--model', default='base',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model size (default: base)')
    parser.add_argument('--no-format', action='store_true',
                        help='Skip Claude formatting step, output raw transcript txt only')
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    run_format = not args.no_format
    if run_format:
        check_dependencies()

    prompt_path = Path(__file__).parent / 'spec' / 'prompt.md'

    if args.file:
        audio_path = Path(args.file)
        txt_path = Path(args.output) / audio_path.with_suffix('.txt').name
        transcribe(audio_path, txt_path, args.model)
        if run_format:
            md_path = txt_path.with_suffix('.md')
            format_transcript(txt_path, md_path, prompt_path)
            print(f"\nDone! Transcript saved to {md_path}")
        else:
            print(f"\nDone! Transcript saved to {txt_path}")
    else:
        video_id, title = get_video_info(args.url)
        paths = build_output_paths(args.output, video_id, title)

        download_audio(args.url, paths['mp3'])
        transcribe(paths['mp3'], paths['txt'], args.model)

        if run_format:
            format_transcript(paths['txt'], paths['md'], prompt_path)
            print(f"\nDone! Transcript saved to {paths['md']}")
        else:
            print(f"\nDone! Transcript saved to {paths['txt']}")


if __name__ == '__main__':
    main()
