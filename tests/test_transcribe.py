from pathlib import Path
from unittest.mock import patch, MagicMock
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


def test_check_dependencies_passes_when_claude_found():
    with patch("shutil.which", return_value="/usr/bin/claude"):
        from transcribe import check_dependencies
        check_dependencies()  # should not raise


def test_check_dependencies_exits_when_claude_missing():
    with patch("shutil.which", return_value=None):
        from transcribe import check_dependencies
        with pytest.raises(SystemExit):
            check_dependencies()


def test_get_video_info_returns_id_and_title():
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = {"id": "dQw4w9WgXcQ", "title": "Never Gonna Give You Up"}

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        from transcribe import get_video_info
        video_id, title = get_video_info("https://youtube.com/watch?v=dQw4w9WgXcQ")

    mock_ydl.extract_info.assert_called_once_with("https://youtube.com/watch?v=dQw4w9WgXcQ", download=False)
    assert video_id == "dQw4w9WgXcQ"
    assert title == "Never Gonna Give You Up"


def test_download_audio_calls_ytdlp():
    mp3_path = Path("output/abc123-some-title.mp3")

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl) as mock_cls:
        from transcribe import download_audio
        download_audio("https://youtube.com/watch?v=abc123", mp3_path)

    mock_ydl.download.assert_called_once_with(["https://youtube.com/watch?v=abc123"])
    opts = mock_cls.call_args[0][0]
    assert opts['postprocessors'][0]['preferredcodec'] == 'mp3'


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


def test_main_wires_pipeline(tmp_path):
    import sys
    sys.argv = [
        'transcribe.py',
        '--url', 'https://youtube.com/watch?v=abc123',
        '--output', str(tmp_path),
        '--model', 'tiny',
    ]

    with patch("transcribe.check_dependencies") as mock_check, \
         patch("transcribe.get_video_info", return_value=("abc123", "Test Video")) as mock_info, \
         patch("transcribe.download_audio") as mock_download, \
         patch("transcribe.transcribe") as mock_transcribe, \
         patch("transcribe.format_transcript") as mock_format:

        from transcribe import main
        main()

    mock_check.assert_called_once()
    mock_info.assert_called_once_with("https://youtube.com/watch?v=abc123")
    mock_download.assert_called_once()
    mock_transcribe.assert_called_once()
    mock_format.assert_called_once()
