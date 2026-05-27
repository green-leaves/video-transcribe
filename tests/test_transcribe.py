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
