# video-transcribe

Transcribe a YouTube video or local audio file to text using Whisper (speech-to-text), with optional Claude-powered formatting into a clean structured markdown file.

## Pipeline

1. Fetch video metadata via `yt-dlp`
2. Download audio as MP3
3. Transcribe with OpenAI Whisper (runs locally) → `.txt`
4. *(optional)* Format and clean the transcript with Claude CLI → `.md`

Output files are saved to `./output/` named `<video-id>-<title-slug>.[mp3|txt|md]`.

## Prerequisites

**Python packages**

```bash
pip install -r requirements.txt
```

**External binary** (required only with `--format`)

| Tool | Install |
|------|---------|
| `claude` | Install [Claude Code CLI](https://claude.ai/code) and run `claude login` |

## Usage

```bash
python transcribe.py --url <YouTube URL> [--output <dir>] [--model <size>] [--format]
python transcribe.py --file <audio file> [--output <dir>] [--model <size>] [--format]
```

`--url` and `--file` are mutually exclusive; one is required.

### Arguments

| Argument | Description |
|----------|-------------|
| `--url` | YouTube video URL — downloads audio and transcribes to `.txt` |
| `--file` | Path to a local audio file (mp3, wav, m4a, …) — transcribes to `.txt` |
| `--format` | Also run the Claude formatting step to produce a cleaned `.md` transcript |
| `--output` | Output directory (default: `./output`) |
| `--model` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` (default: `base`) |

### Examples

```bash
# Transcribe a YouTube video (outputs .mp3 + .txt)
python transcribe.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Transcribe and format with Claude (outputs .mp3 + .txt + .md)
python transcribe.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format

# Transcribe a local audio file (outputs .txt)
python transcribe.py --file recording.mp3

# Transcribe a local file and format with Claude (outputs .txt + .md)
python transcribe.py --file recording.mp3 --format

# Local file with custom output directory and larger model
python transcribe.py --file interview.wav --output ./transcripts --model medium
```

## Whisper Model Sizes

| Model | Parameters | RAM | Speed | Accuracy |
|-------|-----------|-----|-------|----------|
| `tiny` | 39 M | ~1 GB | Fastest | Lowest |
| `base` | 74 M | ~1 GB | Fast | Good |
| `small` | 244 M | ~2 GB | Moderate | Better |
| `medium` | 769 M | ~5 GB | Slow | High |
| `large` | 1550 M | ~10 GB | Slowest | Best |

## Output

For a video with ID `dQw4w9WgXcQ` and title "Never Gonna Give You Up":

```
output/
└── dQw4w9WgXcQ-never-gonna-give-you-up.mp3   # downloaded audio
    dQw4w9WgXcQ-never-gonna-give-you-up.txt   # raw Whisper transcript
    dQw4w9WgXcQ-never-gonna-give-you-up.md    # cleaned markdown transcript (--format only)
```

The markdown file includes YAML frontmatter with topic, tags, source URL, and a short context summary, followed by the transcript split into thematic sections.

## Running Tests

```bash
pip install pytest
pytest tests/
```
