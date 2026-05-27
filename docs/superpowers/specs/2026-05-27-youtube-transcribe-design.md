# YouTube Transcription Pipeline — Design

**Date:** 2026-05-27

## Overview

A single Python script (`transcribe.py`) that takes a YouTube URL and produces a cleaned markdown transcript. It runs three external tools in sequence: yt-dlp (audio download), Whisper (speech-to-text), and the Claude CLI (transcript cleanup using `spec/prompt.md`).

## CLI Interface

```
python transcribe.py --url <youtube-url> [--output ./output] [--model base]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--url` | yes | — | YouTube video URL |
| `--output` | no | `./output` | Directory for all output files |
| `--model` | no | `base` | Whisper model (tiny/base/small/medium/large) |

## File Naming

Video ID and slugified title are combined for all output files. The slug is lowercase, spaces replaced with hyphens, special characters stripped.

Example for video ID `dQw4w9WgXcQ`, title "Never Gonna Give You Up":

- `output/dQw4w9WgXcQ-never-gonna-give-you-up.mp3`
- `output/dQw4w9WgXcQ-never-gonna-give-you-up.txt`
- `output/dQw4w9WgXcQ-never-gonna-give-you-up.md`

The output directory is created automatically if it does not exist.

## Pipeline Steps

Four functions run sequentially:

1. **`get_video_info(url)`** — calls `yt-dlp --dump-json <url>` to fetch video ID and title without downloading. Returns `(video_id, title)`.

2. **`download_audio(url, output_path)`** — calls `yt-dlp -x --audio-format mp3 -o <output_path> <url>` to download audio as MP3.

3. **`transcribe(mp3_path, txt_path, model)`** — loads Whisper model via Python API (`whisper.load_model(model).transcribe(mp3_path)`), writes the resulting text to `txt_path`.

4. **`format_transcript(txt_path, md_path, prompt_path)`** — reads raw transcript, pipes it into the `claude` CLI with the contents of `spec/prompt.md` as the system prompt, writes stdout to `md_path`.

Each step prints a progress line to stdout before executing.

## Error Handling

- **Startup checks:** verify `yt-dlp` and `claude` are on PATH; exit immediately with a clear message if either is missing.
- **Step failures:** any subprocess non-zero exit or Python exception prints the error and exits. No retry logic.
- **Intermediate files:** all files produced before the failure point are kept for debugging.
- No silent failures — all errors surface immediately.

## Dependencies

| Dependency | Type | Install |
|---|---|---|
| `yt-dlp` | system binary | `pip install yt-dlp` or package manager |
| `openai-whisper` | Python package | `pip install openai-whisper` |
| `claude` | system binary | Anthropic CLI |

No `requirements.txt` or `pyproject.toml`. The single pip dependency (`openai-whisper`) is noted in a comment at the top of the script.

## File Structure

```
video-transcribe/
├── transcribe.py        # the script
├── spec/
│   └── prompt.md        # Claude system prompt for transcript cleanup
└── output/              # created at runtime
    ├── <id>-<slug>.mp3
    ├── <id>-<slug>.txt
    └── <id>-<slug>.md
```
