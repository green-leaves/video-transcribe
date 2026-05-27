# YouTube Transcription Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Python script that downloads a YouTube video as MP3, transcribes it with Whisper, then cleans the transcript via the Claude CLI to produce a final markdown file.

**Architecture:** A single `transcribe.py` script with four pipeline functions (`get_video_info`, `download_audio`, `transcribe`, `format_transcript`) wired together by a `main()` that handles CLI args and orchestrates the steps in sequence.

**Tech Stack:** Python 3.10+, `openai-whisper`, `yt-dlp` (system binary), `claude` CLI (system binary), `pytest` + `unittest.mock` for tests.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `transcribe.py` | Create | Main script — all pipeline logic and CLI entrypoint |
| `tests/test_transcribe.py` | Create | Unit tests for all functions |
| `spec/prompt.md` | Existing | Claude system prompt (read-only) |

---

### Task 1: Slug utility and output path builder

**Files:**
- Create: `transcribe.py`
- Create: `tests/test_transcribe.py`

- [ ] **Step 1: Create `tests/test_transcribe.py` with tests for `slugify` and `build_output_paths`**

```python
# tests/test_transcribe.py
from pathlib import Path
from transcribe import slugify, build_output_paths


def test_slugify_lowercases():
    assert slugify("Hello World") == "hello-world"


def test_slugify_strips_special_chars():
    assert slugify("Rick & Morty: Season 1!") == "rick-morty-season-1"


def test_slugify_collapses_spaces():
    assert slugify("a  b   c") == "a-b-c"


def test_slugify_strips_leading_trailing_hyphens():
    assert slugify("  hello  ") == "hello"


def test_build_output_paths_structure():
    paths = build_output_paths("output", "dQw4w9WgXcQ", "Never Gonna Give You Up")
    assert paths["mp3"] == Path("output/dQw4w9WgXcQ-never-gonna-give-you-up.mp3")
    assert paths["txt"] == Path("output/dQw4w9WgXcQ-never-gonna-give-you-up.txt")
    assert paths["md"] == Path("output/dQw4w9WgXcQ-never-gonna-give-you-up.md")
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_transcribe.py -v
```

Expected: `ModuleNotFoundError: No module named 'transcribe'`

- [ ] **Step 3: Create `transcribe.py` with `slugify` and `build_output_paths`**

```python
# transcribe.py
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


def build_output_paths(output_dir: str, video_id: str, title: str) -> dict:
    slug = f"{video_id}-{slugify(title)}"
    base = Path(output_dir) / slug
    return {
        'mp3': base.with_suffix('.mp3'),
        'txt': base.with_suffix('.txt'),
        'md': base.with_suffix('.md'),
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_transcribe.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add slug utility and output path builder"
```

---

### Task 2: Dependency check

**Files:**
- Modify: `transcribe.py` — add `check_dependencies()`
- Modify: `tests/test_transcribe.py` — add tests

- [ ] **Step 1: Add tests for `check_dependencies`**

Append to `tests/test_transcribe.py`:

```python
from unittest.mock import patch
import pytest


def test_check_dependencies_passes_when_all_found():
    with patch("shutil.which", return_value="/usr/bin/yt-dlp"):
        from transcribe import check_dependencies
        check_dependencies()  # should not raise


def test_check_dependencies_exits_when_ytdlp_missing():
    def which_side_effect(name):
        return None if name == "yt-dlp" else "/usr/bin/claude"

    with patch("shutil.which", side_effect=which_side_effect):
        from transcribe import check_dependencies
        with pytest.raises(SystemExit):
            check_dependencies()


def test_check_dependencies_exits_when_claude_missing():
    def which_side_effect(name):
        return None if name == "claude" else "/usr/bin/yt-dlp"

    with patch("shutil.which", side_effect=which_side_effect):
        from transcribe import check_dependencies
        with pytest.raises(SystemExit):
            check_dependencies()
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_transcribe.py::test_check_dependencies_passes_when_all_found -v
```

Expected: `ImportError` or `AttributeError` — `check_dependencies` not defined yet.

- [ ] **Step 3: Add `check_dependencies` to `transcribe.py`**

```python
def check_dependencies() -> None:
    for tool in ('yt-dlp', 'claude'):
        if shutil.which(tool) is None:
            print(f"Error: '{tool}' not found on PATH. Please install it.")
            sys.exit(1)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_transcribe.py -v
```

Expected: all 8 pass.

- [ ] **Step 5: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add startup dependency check"
```

---

### Task 3: `get_video_info`

**Files:**
- Modify: `transcribe.py` — add `get_video_info()`
- Modify: `tests/test_transcribe.py` — add tests

- [ ] **Step 1: Add test for `get_video_info`**

Append to `tests/test_transcribe.py`:

```python
from unittest.mock import patch, MagicMock
import json


def test_get_video_info_returns_id_and_title():
    fake_info = json.dumps({"id": "dQw4w9WgXcQ", "title": "Never Gonna Give You Up"})
    mock_result = MagicMock()
    mock_result.stdout = fake_info

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        from transcribe import get_video_info
        video_id, title = get_video_info("https://youtube.com/watch?v=dQw4w9WgXcQ")

    mock_run.assert_called_once_with(
        ['yt-dlp', '--dump-json', 'https://youtube.com/watch?v=dQw4w9WgXcQ'],
        capture_output=True, text=True, check=True
    )
    assert video_id == "dQw4w9WgXcQ"
    assert title == "Never Gonna Give You Up"
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_transcribe.py::test_get_video_info_returns_id_and_title -v
```

Expected: `ImportError` — `get_video_info` not defined.

- [ ] **Step 3: Add `get_video_info` to `transcribe.py`**

```python
def get_video_info(url: str) -> tuple[str, str]:
    print(f"Fetching video info for {url} ...")
    result = subprocess.run(
        ['yt-dlp', '--dump-json', url],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    return info['id'], info['title']
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_transcribe.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add get_video_info step"
```

---

### Task 4: `download_audio`

**Files:**
- Modify: `transcribe.py` — add `download_audio()`
- Modify: `tests/test_transcribe.py` — add test

- [ ] **Step 1: Add test for `download_audio`**

Append to `tests/test_transcribe.py`:

```python
def test_download_audio_calls_ytdlp():
    mp3_path = Path("output/abc123-some-title.mp3")

    with patch("subprocess.run") as mock_run:
        from transcribe import download_audio
        download_audio("https://youtube.com/watch?v=abc123", mp3_path)

    mock_run.assert_called_once_with(
        ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', str(mp3_path),
         'https://youtube.com/watch?v=abc123'],
        check=True
    )
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_transcribe.py::test_download_audio_calls_ytdlp -v
```

Expected: `ImportError` — `download_audio` not defined.

- [ ] **Step 3: Add `download_audio` to `transcribe.py`**

```python
def download_audio(url: str, output_path: Path) -> None:
    print(f"Downloading audio to {output_path} ...")
    subprocess.run(
        ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', str(output_path), url],
        check=True
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_transcribe.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add download_audio step"
```

---

### Task 5: `transcribe`

**Files:**
- Modify: `transcribe.py` — add `transcribe()`
- Modify: `tests/test_transcribe.py` — add test

- [ ] **Step 1: Add test for `transcribe`**

Append to `tests/test_transcribe.py`:

```python
def test_transcribe_writes_text_to_file(tmp_path):
    mp3_path = tmp_path / "audio.mp3"
    mp3_path.touch()
    txt_path = tmp_path / "audio.txt"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "Hello world transcript."}

    with patch("whisper.load_model", return_value=mock_model) as mock_load:
        from transcribe import transcribe
        transcribe(mp3_path, txt_path, "base")

    mock_load.assert_called_once_with("base")
    mock_model.transcribe.assert_called_once_with(str(mp3_path))
    assert txt_path.read_text() == "Hello world transcript."
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_transcribe.py::test_transcribe_writes_text_to_file -v
```

Expected: `ImportError` — `transcribe` not defined (or `whisper` not imported).

- [ ] **Step 3: Add `import whisper` and `transcribe()` to `transcribe.py`**

Add `import whisper` to the imports block at the top, then add:

```python
def transcribe(mp3_path: Path, txt_path: Path, model: str) -> None:
    print(f"Transcribing {mp3_path} with whisper model '{model}' ...")
    model_obj = whisper.load_model(model)
    result = model_obj.transcribe(str(mp3_path))
    txt_path.write_text(result['text'])
    print(f"Raw transcript written to {txt_path}")
```

- [ ] **Step 4: Install whisper if not already installed**

```
pip install openai-whisper
```

- [ ] **Step 5: Run tests to confirm they pass**

```
pytest tests/test_transcribe.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add whisper transcription step"
```

---

### Task 6: `format_transcript`

**Files:**
- Modify: `transcribe.py` — add `format_transcript()`
- Modify: `tests/test_transcribe.py` — add test

- [ ] **Step 1: Add test for `format_transcript`**

Append to `tests/test_transcribe.py`:

```python
def test_format_transcript_calls_claude_and_writes_md(tmp_path):
    txt_path = tmp_path / "audio.txt"
    txt_path.write_text("raw transcript text")
    md_path = tmp_path / "audio.md"
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("You are a transcript cleaner.")

    mock_result = MagicMock()
    mock_result.stdout = "# Cleaned Transcript\n\nHello world."

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        from transcribe import format_transcript
        format_transcript(txt_path, md_path, prompt_path)

    called_args = mock_run.call_args
    assert called_args[0][0][0] == 'claude'
    assert md_path.read_text() == "# Cleaned Transcript\n\nHello world."
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_transcribe.py::test_format_transcript_calls_claude_and_writes_md -v
```

Expected: `ImportError` — `format_transcript` not defined.

- [ ] **Step 3: Add `format_transcript` to `transcribe.py`**

```python
def format_transcript(txt_path: Path, md_path: Path, prompt_path: Path) -> None:
    print(f"Formatting transcript with Claude ...")
    system_prompt = prompt_path.read_text()
    transcript = txt_path.read_text()
    message = f"{system_prompt}\n\nRaw transcript:\n\n{transcript}"
    result = subprocess.run(
        ['claude', '-p', message],
        capture_output=True, text=True, check=True
    )
    md_path.write_text(result.stdout)
    print(f"Final markdown written to {md_path}")
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_transcribe.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add claude formatting step"
```

---

### Task 7: CLI entrypoint (`main`)

**Files:**
- Modify: `transcribe.py` — add `main()` and `argparse` wiring
- Modify: `tests/test_transcribe.py` — add CLI test

- [ ] **Step 1: Add test for CLI argument parsing**

Append to `tests/test_transcribe.py`:

```python
def test_main_wires_pipeline(tmp_path):
    prompt_path = Path("spec/prompt.md")

    fake_info = json.dumps({"id": "abc123", "title": "Test Video"})
    mock_info_result = MagicMock()
    mock_info_result.stdout = fake_info

    mock_claude_result = MagicMock()
    mock_claude_result.stdout = "# Final MD"

    def subprocess_side_effect(cmd, **kwargs):
        if cmd[0] == 'yt-dlp' and '--dump-json' in cmd:
            return mock_info_result
        if cmd[0] == 'claude':
            return mock_claude_result
        return MagicMock()

    with patch("subprocess.run", side_effect=subprocess_side_effect), \
         patch("shutil.which", return_value="/usr/bin/tool"), \
         patch("whisper.load_model") as mock_whisper, \
         patch("transcribe.Path.mkdir"):

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "raw text"}
        mock_whisper.return_value = mock_model

        from transcribe import main
        import sys
        sys.argv = [
            'transcribe.py',
            '--url', 'https://youtube.com/watch?v=abc123',
            '--output', str(tmp_path),
            '--model', 'base',
        ]
        # Patch write_text to avoid filesystem writes in test
        with patch.object(Path, 'write_text'):
            main()
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_transcribe.py::test_main_wires_pipeline -v
```

Expected: `ImportError` — `main` not defined.

- [ ] **Step 3: Add `main()` to `transcribe.py`**

```python
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video to markdown.")
    parser.add_argument('--url', required=True, help='YouTube video URL')
    parser.add_argument('--output', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--model', default='base',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model size (default: base)')
    args = parser.parse_args()

    check_dependencies()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    video_id, title = get_video_info(args.url)
    paths = build_output_paths(args.output, video_id, title)

    download_audio(args.url, paths['mp3'])
    transcribe(paths['mp3'], paths['txt'], args.model)

    prompt_path = Path(__file__).parent / 'spec' / 'prompt.md'
    format_transcript(paths['txt'], paths['md'], prompt_path)

    print(f"\nDone! Transcript saved to {paths['md']}")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run all tests**

```
pytest tests/test_transcribe.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: add CLI entrypoint and wire pipeline"
```

---

### Task 8: Smoke test with a real video

- [ ] **Step 1: Run the script against a short real video**

```
python transcribe.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --model tiny
```

(Use `--model tiny` for speed during testing.)

Expected:
- `output/dQw4w9WgXcQ-never-gonna-give-you-up.mp3` exists
- `output/dQw4w9WgXcQ-never-gonna-give-you-up.txt` exists with raw transcript
- `output/dQw4w9WgXcQ-never-gonna-give-you-up.md` exists with cleaned markdown matching the `spec/prompt.md` frontmatter format

- [ ] **Step 2: Verify the `.md` file has the expected frontmatter structure**

Open `output/*.md` and confirm it contains:
```
---
type: transcript
topic: ...
tags: ...
interview-date: ...
transcription: whisper-base
source: https://www.youtube.com/watch?v=...
context: ...
---
```

- [ ] **Step 3: Commit if all looks good**

```
git add .
git commit -m "chore: verify smoke test passes"
```
