import base64
from datetime import datetime
import importlib.util
import io
import os
from pathlib import Path
import re
import sys
import unicodedata

import requests
from dotenv import load_dotenv
from PIL import Image
from PIL.ExifTags import TAGS

load_dotenv(Path(__file__).resolve().parent / ".env")

# Ollama configuration
OLLAMA_URL = os.getenv(
    "OLLAMA_URL", "http://localhost:11434/api/generate"
)
MODEL_NAME = os.getenv("OLLAMA_MODEL", "openbmb/minicpm-v4.6")

# Built-in labels. Personal ones are prepended from keywords.local.py.
# The first match in the merged list wins.
# There is no "other": a screen that fits nothing contributes no keyword.
GENERIC_KEYWORDS = [
    "credentials",
    "chat",
    "meeting",
    "diagram",
    "database",
    "git",
    "terminal",
    "code",
    "wireless",
    "directory",
    "project",
    "document",
    "receipt",
    "notes",
    "chart",
    "error",
    "settings",
    "browser",
    "meme",
]

# Words the model may say that should be stored as a listed keyword.
GENERIC_ALIASES = {
    "password": "credentials",
    "passwords": "credentials",
    "passkey": "credentials",
    "login": "credentials",
    "authentication": "credentials",
    "username": "credentials",
    "gitlab": "git",
    "github": "git",
    "flowchart": "diagram",
    "wifi": "wireless",
    "plink": "wireless",
    "order": "receipt",
    "invoice": "receipt",
    "voucher": "receipt",
    "vouchers": "receipt",
    "call": "meeting",
    "letter": "document",
    "website": "browser",
}

GENERIC_GUIDE = """
credentials: a login, password, passkey, or username screen. Never copy the secret
chat: Telegram, Slack, Messenger, or any other chat
meeting: a video call such as Google Meet or Zoom
diagram: a flowchart or node diagram
database: a database console, such as Neo4j
git: Git, GitHub, or GitLab
terminal: a command line
code: source code in an editor
wireless: a Wi-Fi or router wireless panel
directory: a file or folder list
project: a project page
document: a PDF, specification, form, or letter
receipt: an order, invoice, payment, or parcel pickup code
notes: notes or a task list
chart: a plot or chart
error: an error dialog or stack trace
settings: a settings page that is not a password screen
browser: any other website
meme: a joke image
""".strip()


def load_local_keywords():
  """Reads keywords.local.py next to this script. A missing file adds nothing."""
  path = Path(__file__).resolve().parent / "keywords.local.py"
  if not path.exists():
    return [], {}
  spec = importlib.util.spec_from_file_location("keywords_local", path)
  if spec is None or spec.loader is None:
    return [], {}
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return list(getattr(module, "KEYWORDS", [])), dict(getattr(module, "ALIASES", {}))


_local_keywords, _local_aliases = load_local_keywords()

ALLOWED_KEYWORDS = [
    name for name, _hint in _local_keywords
] + GENERIC_KEYWORDS
KEYWORD_ALIASES = {**GENERIC_ALIASES, **_local_aliases}
_local_guide = "\n".join(
    f"{name}: {hint}" for name, hint in _local_keywords
)
KEYWORD_GUIDE = "\n".join(
    part for part in (_local_guide, GENERIC_GUIDE) if part
)

DATE_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_KEYWORD_ALT = "|".join(
    re.escape(keyword)
    for keyword in sorted(ALLOWED_KEYWORDS, key=len, reverse=True)
)
# git.png and git_1.png from the old folder layout.
KNOWN_STEM = re.compile(rf"^(?P<kw>{_KEYWORD_ALT})(?:_\d+)?$")
# git_2025-01-15.png and git_2025-01-15_16-42-14.png, no description yet.
DATED_STEM = re.compile(
    rf"^(?P<kw>{_KEYWORD_ALT})_\d{{4}}-\d{{2}}-\d{{2}}"
    rf"(?:_\d{{2}}-\d{{2}}-\d{{2}}(?:_\d+)?)?$"
)
# 2024-12-12git.png from the flattened names already on disk.
GLUED_STEM = re.compile(
    rf"^(?P<date>\d{{4}}-\d{{2}}-\d{{2}})(?P<kw>{_KEYWORD_ALT})(?:_\d+)?$"
)
SLUG_STOPWORDS = {
    "a", "an", "the", "of", "and", "with", "for", "to", "in", "on",
}
# Older runs stored a failed label as other.png or 2024-12-06other.png.
LEGACY_OTHER = re.compile(
    r"^(?:other(?:_\d+)?|other_\d{4}-\d{2}-\d{2}.*|\d{4}-\d{2}-\d{2}other(?:_\d+)?)$"
)
NEW_NAME = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:_(?P<time>\d{2}-\d{2}-\d{2})(?:_(?P<n>\d+))?)?"
    r"(?:_(?P<rest>.+))?$"
)
VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def get_image_date(file_path):
  """Gets the date from EXIF or falls back to file modification date."""
  try:
    with Image.open(file_path) as img:
      exif_data = img.getexif()
      if exif_data:
        for tag_id, value in exif_data.items():
          tag = TAGS.get(tag_id, tag_id)
          if tag == "DateTimeOriginal":
            return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
  except Exception:
    pass
  return datetime.fromtimestamp(os.path.getmtime(file_path))


def fold_text(value):
  """Lowercase and strip accents so a label still matches its keyword."""
  value = value.strip().lower()
  value = unicodedata.normalize("NFKD", value)
  return "".join(ch for ch in value if not unicodedata.combining(ch))


def pick_keyword(result):
  """Returns a listed keyword, or an empty string when nothing fits."""
  folded = fold_text(result)
  for keyword in ALLOWED_KEYWORDS:
    names = [keyword] + [
        alias for alias, target in KEYWORD_ALIASES.items()
        if target == keyword
    ]
    for name in sorted(names, key=len, reverse=True):
      if re.search(rf"\b{re.escape(name)}\b", folded):
        return keyword
  return ""


def preview_base64(img):
  """Builds a small RGB JPEG. Screenshots are often RGBA, which JPEG rejects."""
  preview = img.copy()
  preview.thumbnail((512, 512))
  if preview.mode != "RGB":
    preview = preview.convert("RGB")
  buffered = io.BytesIO()
  preview.save(buffered, format="JPEG", quality=85)
  return base64.b64encode(buffered.getvalue()).decode("utf-8")


def chat_url():
  if OLLAMA_URL.endswith("/api/generate"):
    return OLLAMA_URL[: -len("/api/generate")] + "/api/chat"
  if OLLAMA_URL.endswith("/api/chat"):
    return OLLAMA_URL
  return OLLAMA_URL.rstrip("/") + "/api/chat"


def looks_like_secret(part):
  """Drops tokens that look like a password, code, or phone number."""
  if len(part) >= 8 and re.search(r"\d", part) and re.search(r"[a-z]", part):
    return True
  if len(part) >= 6 and part.isdigit():
    return True
  return False


def clean_slug(value):
  """Turns a model phrase into 2 or 3 filename words."""
  folded = fold_text(value)
  parts = [
      part for part in re.findall(r"[a-z0-9]+", folded)
      if part not in SLUG_STOPWORDS and not looks_like_secret(part)
  ]
  return "-".join(parts[:3])[:48]


def ask_chat(file_path, prompt, num_predict):
  """One short reply. Thinking is off so the model does not spend the budget on a trace."""
  with Image.open(file_path) as img:
    img_base64 = preview_base64(img)
  payload = {
      "model": MODEL_NAME,
      "stream": False,
      "think": False,
      "messages": [{
          "role": "user",
          "content": prompt,
          "images": [img_base64],
      }],
      "options": {
          "temperature": 0,
          "num_predict": num_predict,
      },
  }
  response = requests.post(chat_url(), json=payload, timeout=120)
  if response.status_code != 200:
    print(f"Ollama returned status {response.status_code}")
    return ""
  body = response.json()
  return ((body.get("message") or {}).get("content") or "").strip()


def ask_model(file_path, known_keyword):
  """Returns (keyword, slug). The slug is empty when the model fails."""
  try:
    slug_text = ask_chat(
        file_path,
        "Name what is visible in 2 or 3 English words. "
        "Use hyphens and no other words. Example: merge-request. "
        "Never write a password, passphrase, API key, token, code, "
        "username, email, or phone number. If a secret is on screen, "
        "name the service instead, such as gitlab-login or wifi-panel.",
        num_predict=24,
    )
    slug = clean_slug(slug_text)
    print(f"Model said: {slug_text}")
    if known_keyword:
      return known_keyword, slug

    label_text = ask_chat(
        file_path,
        "Reply with one word from this list: "
        + ", ".join(ALLOWED_KEYWORDS)
        + ".\n"
        + KEYWORD_GUIDE
        + "\nIf nothing fits, reply none.",
        num_predict=8,
    )
    print(f"Label said: {label_text}")
    return pick_keyword(label_text), slug

  except Exception as e:
    print(f"Error connecting to Ollama: {e}")
    return known_keyword, ""


def split_keyword_slug(rest):
  """Splits 'git_merge-request' into a keyword and a slug."""
  for keyword in sorted(ALLOWED_KEYWORDS, key=len, reverse=True):
    if rest == keyword or re.fullmatch(rf"{re.escape(keyword)}_\d+", rest):
      return keyword, ""
    prefix = keyword + "_"
    if rest.startswith(prefix):
      return keyword, rest[len(prefix):]
  return "", rest


def parse_new_name(stem):
  """Reads YYYY-MM-DD[_HH-MM-SS][_keyword]_slug. None for older shapes."""
  match = NEW_NAME.fullmatch(stem)
  if not match or not match.group("rest"):
    return None
  keyword, slug = split_keyword_slug(match.group("rest"))
  return {"keyword": keyword, "slug": slug, "done": bool(slug)}


def iter_images(source_dir):
  """Images that still need a date and a description in the filename.

  A finished name is YYYY-MM-DD[_HH-MM-SS][_keyword]_slug. Images sitting
  in YYYY-MM-DD folders from an older run are included so they can move back.
  """
  for filename in sorted(os.listdir(source_dir)):
    path = os.path.join(source_dir, filename)
    if os.path.isdir(path):
      if not DATE_FOLDER.fullmatch(filename):
        continue
      for inner in sorted(os.listdir(path)):
        if os.path.splitext(inner)[1].lower() in VALID_EXTENSIONS:
          yield os.path.join(path, inner)
      continue

    stem, ext = os.path.splitext(filename)
    if ext.lower() not in VALID_EXTENSIONS:
      continue
    parsed = parse_new_name(stem)
    if parsed and parsed["done"]:
      continue
    yield path


def display_name(source_dir, source_path):
  parent = os.path.basename(os.path.dirname(source_path))
  filename = os.path.basename(source_path)
  if os.path.abspath(os.path.dirname(source_path)) == os.path.abspath(
      source_dir
  ):
    return filename
  return f"{parent}/{filename}"


def keyword_for(source_path):
  """Reuses a label already in the filename. An old 'other' is not reused."""
  stem = os.path.splitext(os.path.basename(source_path))[0]
  if LEGACY_OTHER.fullmatch(stem):
    return None
  parsed = parse_new_name(stem)
  if parsed and parsed["keyword"]:
    return parsed["keyword"]
  known = (
      KNOWN_STEM.fullmatch(stem)
      or DATED_STEM.fullmatch(stem)
      or GLUED_STEM.fullmatch(stem)
  )
  if known:
    return known.group("kw")
  return None


def path_is_free(path, source_path):
  return (
      os.path.abspath(path) == os.path.abspath(source_path)
      or not os.path.exists(path)
  )


def build_filename(date_stamp, keyword, slug, ext, time_stamp=None, counter=None):
  """YYYY-MM-DD[_HH-MM-SS][_keyword]_slug. The keyword is omitted when empty."""
  parts = [date_stamp]
  if time_stamp:
    parts.append(time_stamp)
  if counter:
    parts.append(str(counter))
  if keyword:
    parts.append(keyword)
  if slug:
    parts.append(slug)
  return "_".join(parts) + ext


def target_path_for(source_dir, source_path, keyword, slug):
  """Date, then keyword, then slug. Adds HH-MM-SS when that name is taken."""
  file_dt = get_image_date(source_path)
  ext = os.path.splitext(source_path)[1].lower()
  date_stamp = file_dt.strftime("%Y-%m-%d")
  time_stamp = file_dt.strftime("%H-%M-%S")
  plain = os.path.join(
      source_dir,
      build_filename(date_stamp, keyword, slug, ext),
  )
  if path_is_free(plain, source_path):
    return plain

  timed = os.path.join(
      source_dir,
      build_filename(date_stamp, keyword, slug, ext, time_stamp),
  )
  if path_is_free(timed, source_path):
    return timed

  counter = 2
  while counter < 1000:
    path = os.path.join(
        source_dir,
        build_filename(
            date_stamp, keyword, slug, ext, time_stamp, counter
        ),
    )
    if path_is_free(path, source_path):
      return path
    counter += 1
  raise RuntimeError(f"Too many name collisions for {source_path}")


def remove_empty_date_folders(source_dir):
  for filename in os.listdir(source_dir):
    path = os.path.join(source_dir, filename)
    if not DATE_FOLDER.fullmatch(filename) or not os.path.isdir(path):
      continue
    if not os.listdir(path):
      os.rmdir(path)


def organize_images_with_ai(source_dir):
  if not os.path.exists(source_dir):
    print(f"Error: The path '{source_dir}' does not exist.")
    return

  processed_count = 0
  skipped_count = 0

  print(
      f"Starting sorting with model '{MODEL_NAME}' using English keywords..."
  )

  for source_path in list(iter_images(source_dir)):
    label = display_name(source_dir, source_path)
    print(f"Analyzing: {label}...")
    keyword, slug = ask_model(
        source_path, keyword_for(source_path)
    )
    if not keyword and not slug:
      print(f"Skipped, file left in place: {label}")
      skipped_count += 1
      continue

    target_path = target_path_for(source_dir, source_path, keyword, slug)
    if os.path.abspath(target_path) != os.path.abspath(source_path):
      os.rename(source_path, target_path)
    print(f"✅ {label} -> {os.path.basename(target_path)}")
    processed_count += 1

  remove_empty_date_folders(source_dir)
  print(
      f"\nDone! Processed files: {processed_count}. Skipped: {skipped_count}"
  )


def resolve_source_dir():
  """CLI path, then PHOTOS_DIR from .env, then an interactive prompt."""
  if len(sys.argv) > 1:
    path_to_sort = sys.argv[1].strip()
  else:
    path_to_sort = os.getenv("PHOTOS_DIR", "").strip()
  if not path_to_sort:
    path_to_sort = input(
        "Enter the path to the folder with images: "
    ).strip()
  if not path_to_sort:
    path_to_sort = "."
  return os.path.expanduser(path_to_sort)


if __name__ == "__main__":
  organize_images_with_ai(resolve_source_dir())
