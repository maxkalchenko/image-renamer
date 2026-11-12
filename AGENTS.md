# image-renamer

Local, in-place sorter for a flat folder of screenshots. There is no web UI, database, or upload step. `script.py` is the whole program.

## Flow

`organize_images_with_ai` lists the top level of the source directory. For each image it:

1. `get_image_date` — EXIF `DateTimeOriginal` from the Exif IFD (`%Y:%m:%d %H:%M:%S`), else `DateTime`, else file birth time, else mtime. The date and time go into the filename. No directory is created.
2. `keyword_for` reuses a keyword already in the filename (`git.png`, `2024-12-12git.png`, `git_2025-01-15.png`). `ask_model` calls Ollama `/api/chat` with thinking disabled and asks for a 4–6 word slug. A file with no keyword gets a second short call for the label.
3. `os.rename` inside `IMG_DIR` to `[device_]YYYY-MM-DD_HH-MM-SS_<keyword>_<slug>.<ext>`. The device is the EXIF model when the file has one (`canon-eos-r6m2`, `iphone-14-pro`, `samsung-sm-s928b`). With no model, an XMP or EXIF `Screenshot` comment uses `screenshot`. With neither, the name starts at the date. With no keyword the keyword segment is left out. A taken name inserts `_2`, `_3`, … after the time.

Files that already include the slug are skipped, including older names that have no clock time. A keyword and date without a slug are described again. Images inside a `YYYY-MM-DD` folder from an older run are moved back to `IMG_DIR`, and the empty date folder is removed. If the model reply is cut off, the file stays where it is.

## Configuration

Runtime settings live in `.env` (see `.env.example`). `script.py` loads the file next to itself.

| Variable | Role |
| --- | --- |
| `IMG_DIR` | Folder to sort. CLI argument overrides it. Empty value falls through to an interactive prompt, then `.` |
| `OLLAMA_URL` | Generate endpoint. Default `http://localhost:11434/api/generate` |
| `OLLAMA_MODEL` | Vision model id. Default `openbmb/minicpm-v4.6` |

Built-in labels stay in `GENERIC_KEYWORDS`. Personal labels live in gitignored `keywords.local.py` and are prepended into `ALLOWED_KEYWORDS`. Changing a label renames future files only.

## Constraints

- Sorting renames files inside `IMG_DIR`. Do not create date folders. Do not point it at a folder you cannot restore.
- Keep built-in labels in `GENERIC_KEYWORDS`, specific ones first, with one line in `GENERIC_GUIDE`. Screen labels stay ahead of `people`, `animal`, `food`, and `nature`. Personal labels go in `keywords.local.py`, also specific first, and are prepended into `ALLOWED_KEYWORDS`. The prompt glossary is the merged `KEYWORD_GUIDE`. Do not add an `other` label. Map extra words through `GENERIC_ALIASES` or the local `ALIASES`. A camera photograph that fits none of the definitions contributes no keyword.
- Never put a password, key, token, code, username, email, or phone number in a slug. Login screens use `credentials` and describe the service.
- A request or encode failure leaves the file where it is. A missing keyword still allows a rename when the slug exists.
- Screenshots are often RGBA. Convert the preview to RGB before saving JPEG.
- Dependencies are `Pillow`, `requests`, and `python-dotenv`, declared in `requirements.txt`.
- Match the 2-space indent already used in `script.py`.
- Comments, docs, and identifiers stay in English. Chat replies to the user stay in Ukrainian.
- `.env` and `keywords.local.py` are gitignored. Commit `.env.example` when the variable set changes, and `keywords.local.example.py` when the local keyword format changes.
