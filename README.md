# image-renamer

Local sorter for screenshots and images. `script.py` asks a vision model running in [Ollama](https://ollama.com) for one keyword and a short description, then renames each image in the same folder. `group.py` later moves root images into date folders. The renamer itself does not create folders.

## What it does

For each `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, and `.heif` file in the source folder:

1. Reads `DateTimeOriginal` from the EXIF sub-block. If that is missing, it uses `DateTime`, then the file creation time, then the modification time.
2. Sends a 512px JPEG preview to Ollama. The model returns a 4–6 word description. A file that already carries a keyword keeps it; otherwise the model also picks the keyword.
3. Renames it to `[device_]YYYY-MM-DD_HH-MM-SS_<keyword>_<slug>.<ext>` in `IMG_DIR`. A camera or phone model becomes the first word when EXIF has one: `canon-eos-r6m2_2025-05-06_13-36-11_nature_forest-trail.jpg`. An iPhone model drops the Apple brand: `iphone-14-pro_...`. A code such as `SM-S928B` keeps the make: `samsung-sm-s928b_...`. With no model, an XMP or EXIF comment of `Screenshot` uses `screenshot_...`. With neither, the name starts at the date: `2025-01-15_16-42-14_git_merge-request-diff.png`. When no keyword fits, the keyword is left out.
4. If that name is already taken, inserts `_2`, `_3`, and so on after the time.

A file that already has the date and a slug is left alone, including older names that have no clock time. A name with only the keyword and the date is sent back so the model can add the description. Files that already sit in a subfolder stay there.

Built-in keywords, most specific first: `credentials`, `chat`, `meeting`, `diagram`, `database`, `git`, `terminal`, `code`, `wireless`, `directory`, `project`, `document`, `receipt`, `notes`, `chart`, `error`, `settings`, `browser`, `meme`, `people`, `animal`, `food`, `nature`. Personal labels live in `keywords.local.py` (see `keywords.local.example.py`) and are checked first. That file is gitignored.

There is no `other`. A password, login, or passkey screen is `credentials`, and the slug names the service (`gitlab-login`, `wifi-panel`) rather than the secret itself. GitHub and GitLab are `git`. A camera photograph uses `people`, `animal`, `food`, or `nature`. When none of the definitions fit, the keyword is left out and the slug carries the description.

PNG screenshots are converted to RGB before the JPEG preview. If Ollama cannot be reached, the file stays where it is.

## Requirements

- Python 3.10+
- Ollama running locally
- The vision model named in `OLLAMA_MODEL` (default `openbmb/minicpm-v4.6`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # skip if .env already exists
cp keywords.local.example.py keywords.local.py   # optional personal labels
```

Set `IMG_DIR` in `.env` to the folder you want to sort. Paths may start with `~`.

Pull the model once:

```bash
ollama pull openbmb/minicpm-v4.6
```

## Run

```bash
python script.py
```

A path passed on the command line overrides `IMG_DIR`:

```bash
python script.py ~/Pictures/Screenshots
```

If neither is set, the script asks for a path. An empty answer sorts the current directory.

Moving files is immediate and in place. Point `IMG_DIR` at a copy if you want to try the sorter first.

## Group into date folders

`group.py` reads images that are still in the root of `IMG_DIR`. It uses the same date as the renamer and does not rename files or call Ollama. Subfolders, videos, and other files stay where they are.

Photos are ordered by time. A new cluster starts when two neighboring photos are 3 hours or more apart. A cluster may cross midnight when the gap is shorter. A cluster of at least 9 files is moved into a folder named with the first photo's date: `2026-11-10`. A second cluster that starts on that same date becomes `2026-11-10_2`, then `_3`. An existing folder of that name is left alone, and the new cluster takes the next free suffix. A cluster with fewer than 9 files stays in the root.

```bash
python group.py
python group.py --dry-run ~/Pictures/Screenshots
```

`--dry-run` prints the groups and moves nothing. A path on the command line overrides `IMG_DIR`. The same fallback as `script.py` applies: an empty `IMG_DIR` asks for a path, and an empty answer uses the current directory.

## Development

Install the development tools into the same virtual environment and turn on the git hooks:

```bash
pip install -r requirements-dev.txt
make hooks
```

| Command | What it runs |
| --- | --- |
| `make lint` | `ruff check .` |
| `make format` | `ruff check --fix .` and `ruff format .` |
| `make format-check` | `ruff format --check .` |
| `make test` | `pytest` |
| `make check` | lint, format check, and tests |

Ruff is configured in `pyproject.toml`: 2-space indent, 80 columns. The tests cover the naming and clustering helpers and never call Ollama. The pre-commit hooks run Ruff and [gitleaks](https://github.com/gitleaks/gitleaks) on every commit. GitHub Actions runs the same checks, plus a gitleaks scan of the whole history, on each push and pull request.

## License

[MIT](LICENSE)
