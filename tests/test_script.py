"""Tests for the pure naming helpers in script.py. Ollama is never called."""

from datetime import datetime
import os

from PIL import Image
from PIL.ExifTags import IFD
import pytest

import script

TAKEN_AT = datetime(2025, 1, 15, 16, 42, 14)


def make_image(path, exif=None, image_format=None):
  img = Image.new("RGB", (4, 4), "white")
  if exif is None:
    img.save(path, format=image_format)
  else:
    img.save(path, format=image_format, exif=exif)
  return path


@pytest.mark.parametrize(
  ("text", "expected"),
  [
    ("A GitLab merge request diff", "gitlab-merge-request-diff"),
    ("gitlab-merge-request-diff", "gitlab-merge-request-diff"),
    ("Café Menü", "cafe-menu"),
    ("one two three four five six seven eight", "one-two-three-four-five-six"),
    ("login hunter2abc 123456 page", "login-page"),
    ("", ""),
  ],
)
def test_clean_slug(text, expected):
  assert script.clean_slug(text) == expected


def test_clean_slug_stays_under_72_characters():
  slug = script.clean_slug(" ".join(["extraordinarily"] * 6))
  assert len(slug) <= 72
  assert slug.split("-") == ["extraordinarily"] * 4


@pytest.mark.parametrize(
  ("part", "expected"),
  [
    ("abc12345", True),
    ("123456", True),
    ("12345", False),
    ("gitlab", False),
    ("v2", False),
  ],
)
def test_looks_like_secret(part, expected):
  assert script.looks_like_secret(part) is expected


def test_build_filename_full():
  name = script.build_filename(
    "2025-01-15",
    "git",
    "merge-request-diff",
    ".png",
    "16-42-14",
    counter=2,
    device="iphone-14-pro",
  )
  assert (
    name == "iphone-14-pro_2025-01-15_16-42-14_2_git_merge-request-diff.png"
  )


def test_build_filename_without_device_and_keyword():
  name = script.build_filename(
    "2025-01-15", "", "forest-trail", ".jpg", "16-42-14"
  )
  assert name == "2025-01-15_16-42-14_forest-trail.jpg"


@pytest.mark.parametrize(
  ("stem", "expected"),
  [
    (
      "2025-01-15_16-42-14_git_merge-request-diff",
      {"keyword": "git", "slug": "merge-request-diff", "done": True},
    ),
    (
      "screenshot_2025-01-15_16-42-14_2_git_merge-request-diff",
      {"keyword": "git", "slug": "merge-request-diff", "done": True},
    ),
    (
      "2025-01-15_forest-trail",
      {"keyword": "", "slug": "forest-trail", "done": True},
    ),
    (
      "2025-01-15_16-42-14_git",
      {"keyword": "git", "slug": "", "done": False},
    ),
    ("2025-01-15", None),
    ("IMG_1234", None),
    ("git", None),
  ],
)
def test_parse_new_name(stem, expected):
  assert script.parse_new_name(stem) == expected


@pytest.mark.parametrize(
  ("rest", "expected"),
  [
    ("git_merge-request-diff", ("git", "merge-request-diff")),
    ("git", ("git", "")),
    ("git_2", ("git", "")),
    ("forest-trail", ("", "forest-trail")),
  ],
)
def test_split_keyword_slug(rest, expected):
  assert script.split_keyword_slug(rest) == expected


@pytest.mark.parametrize(
  ("filename", "expected"),
  [
    ("git.png", "git"),
    ("git_1.png", "git"),
    ("2024-12-12git.png", "git"),
    ("git_2025-01-15.png", "git"),
    ("git_2025-01-15_16-42-14.png", "git"),
    ("2025-01-15_16-42-14_credentials_gitlab-login.png", "credentials"),
    ("other.png", None),
    ("2024-12-06other.png", None),
    ("IMG_1234.png", None),
  ],
)
def test_keyword_for(filename, expected):
  assert script.keyword_for(f"/photos/{filename}") == expected


@pytest.mark.parametrize(
  ("reply", "expected"),
  [
    ("git", "git"),
    ("GitHub", "git"),
    ("Password.", "credentials"),
    ("a portrait", "people"),
    ("none", ""),
    ("", ""),
  ],
)
def test_pick_keyword(reply, expected):
  assert script.pick_keyword(reply) == expected


@pytest.mark.parametrize(
  ("make", "model", "expected"),
  [
    ("Apple", "iPhone 14 Pro", "iphone-14-pro"),
    ("Canon", "Canon EOS R6m2", "canon-eos-r6m2"),
    ("samsung", "SM-S928B", "samsung-sm-s928b"),
    ("Sony", "", "sony"),
    ("", "", ""),
  ],
)
def test_device_from_make_model(make, model, expected):
  assert script.device_from_make_model(make, model) == expected


@pytest.mark.parametrize(
  ("configured", "expected"),
  [
    ("http://localhost:11434/api/generate", "http://localhost:11434/api/chat"),
    ("http://localhost:11434/api/chat", "http://localhost:11434/api/chat"),
    ("http://localhost:11434/", "http://localhost:11434/api/chat"),
  ],
)
def test_chat_url(monkeypatch, configured, expected):
  monkeypatch.setattr(script, "OLLAMA_URL", configured)
  assert script.chat_url() == expected


def test_get_image_date_reads_exif_datetime(tmp_path):
  exif = Image.Exif()
  exif[0x0132] = "2025:01:15 16:42:14"
  path = make_image(tmp_path / "photo.jpg", exif)
  assert script.get_image_date(path) == TAKEN_AT


def test_get_image_date_prefers_datetime_original(tmp_path):
  exif = Image.Exif()
  exif[0x0132] = "2025:02:01 08:00:00"
  exif.get_ifd(IFD.Exif)[0x9003] = "2025:01:15 16:42:14"
  path = make_image(tmp_path / "photo.jpg", exif)
  assert script.get_image_date(path) == TAKEN_AT


def test_get_image_date_falls_back_to_file_time(tmp_path):
  path = make_image(tmp_path / "shot.png")
  assert isinstance(script.get_image_date(path), datetime)


def test_device_slug_from_exif_model(tmp_path):
  exif = Image.Exif()
  exif[0x010F] = "Apple"
  exif[0x0110] = "iPhone 14 Pro"
  path = make_image(tmp_path / "photo.jpg", exif)
  assert script.device_slug(path) == "iphone-14-pro"


def test_device_slug_empty_without_metadata(tmp_path):
  path = make_image(tmp_path / "shot.png")
  assert script.device_slug(path) == ""


def test_preview_base64_accepts_rgba():
  img = Image.new("RGBA", (800, 600), (255, 0, 0, 128))
  assert script.preview_base64(img)


def test_target_path_for_adds_counter_when_taken(tmp_path, monkeypatch):
  monkeypatch.setattr(script, "get_image_date", lambda _path: TAKEN_AT)
  source = make_image(tmp_path / "IMG_1234.PNG", image_format="PNG")
  base = "2025-01-15_16-42-14"

  first = script.target_path_for(
    str(tmp_path), str(source), "git", "merge-request-diff"
  )
  assert first == str(tmp_path / f"{base}_git_merge-request-diff.png")

  (tmp_path / f"{base}_git_merge-request-diff.png").touch()
  second = script.target_path_for(
    str(tmp_path), str(source), "git", "merge-request-diff"
  )
  assert second == str(tmp_path / f"{base}_2_git_merge-request-diff.png")

  (tmp_path / f"{base}_2_git_merge-request-diff.png").touch()
  third = script.target_path_for(
    str(tmp_path), str(source), "git", "merge-request-diff"
  )
  assert third == str(tmp_path / f"{base}_3_git_merge-request-diff.png")


def test_iter_images_skips_finished_names_and_subfolders(tmp_path):
  for name in (
    "a.png",
    "B.JPG",
    "notes.txt",
    "2025-01-15_16-42-14_git.png",
    "2025-01-15_16-42-14_git_merge-request-diff.png",
  ):
    (tmp_path / name).touch()
  (tmp_path / "sub").mkdir()
  (tmp_path / "sub" / "c.png").touch()

  found = [os.path.basename(path) for path in script.iter_images(tmp_path)]
  assert found == ["2025-01-15_16-42-14_git.png", "B.JPG", "a.png"]
