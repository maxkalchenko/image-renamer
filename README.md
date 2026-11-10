# Photos

Local sorter for screenshots and photos. It asks a vision model running in [Ollama](https://ollama.com) for one keyword and a short description, then renames each image in the same folder. It does not create folders.

## What it does

For each `.jpg`, `.jpeg`, `.png`, and `.webp` file in the source folder:

1. Reads `DateTimeOriginal` from EXIF. If that is missing, it uses the file modification time.
2. Sends a 512px JPEG preview to Ollama. The model returns a 2–3 word description. A file that already carries a keyword keeps it; otherwise the model also picks the keyword.
3. Renames it to `YYYY-MM-DD_<keyword>_<short-slug>.<ext>` in `PHOTOS_DIR`. Example: `2025-01-15_git_merge-request.png`. When no keyword fits, the keyword is left out: `2025-01-15_screen-snippet.png`.
4. If that name is already taken, inserts `_HH-MM-SS` after the date.

Files left in `YYYY-MM-DD` folders by an older run are moved back into `PHOTOS_DIR` and those empty folders are removed. A file that already has the keyword, the date, and a slug is left alone. A name with only the keyword and the date is sent back so the model can add the description.

Built-in keywords, most specific first: `credentials`, `chat`, `meeting`, `diagram`, `database`, `git`, `terminal`, `code`, `wireless`, `directory`, `project`, `document`, `receipt`, `notes`, `chart`, `error`, `settings`, `browser`, `meme`. Personal labels live in `keywords.local.py` (see `keywords.local.example.py`) and are checked first. That file is gitignored.

There is no `other`. A password, login, or passkey screen is `credentials`, and the slug names the service (`gitlab-login`, `wifi-panel`) rather than the secret itself. GitHub and GitLab are `git`.

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

Set `PHOTOS_DIR` in `.env` to the folder you want to sort. Paths may start with `~`.

Pull the model once:

```bash
ollama pull openbmb/minicpm-v4.6
```

## Run

```bash
python script.py
```

A path passed on the command line overrides `PHOTOS_DIR`:

```bash
python script.py ~/Pictures/Screenshots
```

If neither is set, the script asks for a path. An empty answer sorts the current directory.

Moving files is immediate and in place. Point `PHOTOS_DIR` at a copy if you want to try the sorter first.
