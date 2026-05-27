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
