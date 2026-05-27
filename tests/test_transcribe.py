from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import pytest
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
