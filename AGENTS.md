# image-renamer

Local, in-place sorter for a flat folder of screenshots. There is no web UI, database, or upload step. `script.py` renames files. `group.py` moves root images into date folders.

## Flow

`organize_images_with_ai` lists the top level of the source directory. For each image it:

1. `get_image_date` — EXIF `DateTimeOriginal` from the Exif IFD (`%Y:%m:%d %H:%M:%S`), else `DateTime`, else file birth time, else mtime. The date and time go into the filename. No directory is created.
2. `keyword_for` reuses a keyword already in the filename (`git.png`, `2024-12-12git.png`, `git_2025-01-15.png`). `ask_model` calls Ollama `/api/chat` with thinking disabled and asks for a 4–6 word slug. A file with no keyword gets a second short call for the label.
3. `os.rename` inside `IMG_DIR` to `[device_]YYYY-MM-DD_HH-MM-SS_<keyword>_<slug>.<ext>`. The device is the EXIF model when the file has one (`canon-eos-r6m2`, `iphone-14-pro`, `samsung-sm-s928b`). With no model, an XMP or EXIF `Screenshot` comment uses `screenshot`. With neither, the name starts at the date. With no keyword the keyword segment is left out. A taken name inserts `_2`, `_3`, … after the time.

Files that already include the slug are skipped, including older names that have no clock time. A keyword and date without a slug are described again. Subfolders are left alone. If the model reply is cut off, the file stays where it is.

`group.py` lists image files in the root only. It sorts them with `get_image_date` and starts a new cluster when neighboring photos are 3 hours or more apart. A cluster may cross midnight. A cluster of at least 9 files is moved into a folder named with the first photo's date (`YYYY-MM-DD`). Another cluster that starts on that same date uses `_2`, `_3`, and so on when the name is already taken. A smaller cluster stays in the root. `--dry-run` prints the groups and moves nothing.

## Configuration

Runtime settings live in `.env` (see `.env.example`). `script.py` loads the file next to itself.

| Variable | Role |
| --- | --- |
| `IMG_DIR` | Folder to sort. CLI argument overrides it. Empty value falls through to an interactive prompt, then `.` |
| `OLLAMA_URL` | Generate endpoint. Default `http://localhost:11434/api/generate` |
| `OLLAMA_MODEL` | Vision model id. Default `openbmb/minicpm-v4.6` |

Built-in labels stay in `GENERIC_KEYWORDS`. Personal labels live in gitignored `keywords.local.py` and are prepended into `ALLOWED_KEYWORDS`. Changing a label renames future files only.

## Constraints

- Sorting renames files in the root of `IMG_DIR`. `group.py` is what creates date folders: a gap of 3 hours or more starts a cluster, a cluster needs at least 9 files, and the folder name is the first photo's date. Do not point either script at a folder you cannot restore.
- Keep built-in labels in `GENERIC_KEYWORDS`, specific ones first, with one line in `GENERIC_GUIDE`. Screen labels stay ahead of `people`, `animal`, `food`, and `nature`. Personal labels go in `keywords.local.py`, also specific first, and are prepended into `ALLOWED_KEYWORDS`. The prompt glossary is the merged `KEYWORD_GUIDE`. Do not add an `other` label. Map extra words through `GENERIC_ALIASES` or the local `ALIASES`. A camera photograph that fits none of the definitions contributes no keyword.
- Never put a password, key, token, code, username, email, or phone number in a slug. Login screens use `credentials` and describe the service.
- A request or encode failure leaves the file where it is. A missing keyword still allows a rename when the slug exists.
- Screenshots are often RGBA. Convert the preview to RGB before saving JPEG.
- Dependencies are `Pillow`, `pillow-heif`, `requests`, and `python-dotenv`, declared in `requirements.txt`. `pillow-heif` registers HEIC and HEIF so `Image.open` can read them. The file on disk keeps its extension.
- Development tools (`ruff`, `pytest`, `pre-commit`) are declared in `requirements-dev.txt` and configured in `pyproject.toml`. They are not runtime dependencies.
- `ruff format` owns the style: 2-space indent, 80 columns. Run `make check` (lint, format check, tests) before committing. `make format` applies the fixes.
- Tests live in `tests/` and never call Ollama. Add a case there when a naming or clustering rule changes.
- Comments, docs, and identifiers stay in English. Chat replies to the user stay in Ukrainian.
- `.env` and `keywords.local.py` are gitignored. Commit `.env.example` when the variable set changes, and `keywords.local.example.py` when the local keyword format changes.
