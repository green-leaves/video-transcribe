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


def _confirm(question: str) -> bool:
    try:
        answer = input(f"{question} [Y/n] ").strip().lower()
    except EOFError:
        return True
    return answer in ('', 'y', 'yes')


def _vtt_to_text(vtt_path: Path) -> str:
    out: list[str] = []
    for line in vtt_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(('WEBVTT', 'Kind:', 'Language:', 'NOTE')):
            continue
        if '-->' in line or line.isdigit():
            continue
        line = re.sub(r'<[^>]+>', '', line).strip()  # strip inline timing/color tags
        if not line:
            continue
        if out and out[-1] == line:  # collapse rolling-caption duplicates
            continue
        out.append(line)
    return '\n'.join(out)


def fetch_subtitles(url: str, base_path: Path, lang: str) -> Path | None:
    print(f"Checking for '{lang}' subtitles ...")
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)

    manual = info.get('subtitles') or {}
    auto = info.get('automatic_captions') or {}
    if lang in manual:
        print(f"Found uploaded '{lang}' subtitles.")
        if not _confirm(f"Use uploaded '{lang}' subtitles instead of transcribing audio?"):
            print("Skipping uploaded subtitles; will transcribe audio instead.")
            return None
        write_opts = {'writesubtitles': True, 'writeautomaticsub': False}
    elif lang in auto:
        print(f"Found auto-generated '{lang}' captions.")
        write_opts = {'writesubtitles': False, 'writeautomaticsub': True}
    else:
        print(f"No '{lang}' subtitles available; will transcribe audio instead.")
        return None

    ydl_opts = {
        'skip_download': True,
        'subtitleslangs': [lang],
        'subtitlesformat': 'vtt',
        'outtmpl': str(base_path),
        'quiet': True,
        **write_opts,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    vtt_path = base_path.with_name(f"{base_path.name}.{lang}.vtt")
    if not vtt_path.exists():
        matches = sorted(base_path.parent.glob(f"{base_path.name}.{lang}*.vtt"))
        if not matches:
            print("Subtitle download reported success but no file was written.")
            return None
        vtt_path = matches[0]
    return vtt_path


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


def transcribe(mp3_path: Path, txt_path: Path, model: str, lang: str) -> None:
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Transcribing {mp3_path} with whisper model '{model}' on {device} ...")
    model_obj = whisper.load_model(model, device=device)
    result = model_obj.transcribe(str(mp3_path), verbose=True, language=lang)
    txt_path.write_text(result['text'], encoding='utf-8')
    print(f"Raw transcript written to {txt_path}")


def format_transcript(txt_path: Path, md_path: Path, prompt_path: Path) -> None:
    print("Formatting transcript with Claude ...")
    system_prompt = prompt_path.read_text(encoding='utf-8')
    transcript = txt_path.read_text(encoding='utf-8')
    message = f"{system_prompt}\n\nRaw transcript:\n\n{transcript}"
    result = subprocess.run(
        ['claude', '-p'],
        input=message,
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
    parser.add_argument('--model', default='medium',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model size (default: base)')
    parser.add_argument('--lang', default='en',
                        help='Subtitle/transcription language code (default: en)')
    parser.add_argument('--force-transcribe', action='store_true',
                        help='Skip the YouTube subtitle fast path and always transcribe the audio')
    parser.add_argument('--format', action='store_true',
                        help='Run Claude formatting step to produce a cleaned markdown transcript')
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    if args.format:
        check_dependencies()

    prompt_path = Path(__file__).parent / 'spec' / 'prompt.md'

    if args.file:
        audio_path = Path(args.file)
        if audio_path.suffix.lower() == '.txt':
            txt_path = audio_path
        else:
            txt_path = Path(args.output) / audio_path.with_suffix('.txt').name
            transcribe(audio_path, txt_path, args.model, args.lang)
        if args.format:
            md_path = txt_path.with_suffix('.md')
            format_transcript(txt_path, md_path, prompt_path)
            print(f"\nDone! Transcript saved to {md_path}")
        else:
            print(f"\nDone! Transcript saved to {txt_path}")
    else:
        video_id, title = get_video_info(args.url)
        paths = build_output_paths(args.output, video_id, title)

        got_subs = False
        if not args.force_transcribe:
            vtt_path = fetch_subtitles(args.url, paths['txt'].with_suffix(''), args.lang)
            if vtt_path:
                paths['txt'].write_text(_vtt_to_text(vtt_path), encoding='utf-8')
                print(f"Subtitle transcript written to {paths['txt']}")
                got_subs = True

        if not got_subs:
            download_audio(args.url, paths['mp3'])
            transcribe(paths['mp3'], paths['txt'], args.model, args.lang)

        if args.format:
            format_transcript(paths['txt'], paths['md'], prompt_path)
            print(f"\nDone! Transcript saved to {paths['md']}")
        else:
            print(f"\nDone! Transcript saved to {paths['txt']}")


if __name__ == '__main__':
    main()
