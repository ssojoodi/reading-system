# Personal Librarian

A reading system for progressing through difficult non-contemporary books in small chunks, generating a plain-English interpretation for each chunk, and sending the latest reading as an HTML email.

## What It Does

- Tracks reading progress per book.
- Generates an interpretation through an OpenAI-compatible API.
- Writes a standalone HTML reading artifact.
- Emails the latest HTML artifact through Mailgun.
- Works well with cron or another scheduler for automated daily delivery.

## Project Layout

```text
.
├── books/
│   ├── library/        # Source book files
│   ├── reading/        # Per-book progress state
│   ├── finished/       # Completed book state / notes
│   └── summaries/      # Reserved for recap/summaries
├── docs/
│   └── reference.md
├── output_files/       # Generated HTML output (gitignored)
├── logs/               # Logs (gitignored)
├── AGENTS.md
├── CONTRIBUTING.md
├── read-book.py
├── send-daily.sh
└── setup.sh
```

## Requirements

- Python 3.10+
- A plain-text book file in `books/library/`
- An OpenAI-compatible model endpoint for interpretation generation
- Optional: Mailgun credentials for email delivery
- Optional: a scheduler such as cron

## Quickstart

### 1. Install dependencies

```bash
uv venv
uv pip install -r requirements.txt
```

### 2. Create the working directories

```bash
./setup.sh
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

### 4. Add a book

- Put a `.txt` book in `books/library/`, project Gutenberg is a good source for public domain books
- `uv run python read-book.py start <book_id>` will create `books/reading/<book_id>.json` automatically if it does not already exist
- See [docs/reference.md](docs/reference.md) for the state file shape and command reference

### 5. Start reading

```bash
uv run python read-book.py start <book_id> # --line 120 is optional to start from a specific line
uv run python read-book.py next <book_id>
uv run python read-book.py status
```

Note: `<book_id>` is the filename of the book in `books/library/` without the `.txt` extension.
The `next` command writes an HTML file to `output_files/` and advances progress in `books/reading/<book_id>.json`.

## Email Delivery Options

### Mailgun

The default email script is [send-daily.sh](send-daily.sh). It reads the newest `.html` file in `output_files/` and sends it as an HTML email body using Mailgun.

```bash
./send-daily.sh --dry-run
./send-daily.sh
```

Required environment variables:

- `MAILGUN_API_KEY`
- `MAILGUN_DOMAIN`
- `RECIPIENTS`

## Core Commands

```bash
uv run python read-book.py start <book_id>
uv run python read-book.py next [book_id]
uv run python read-book.py status
```

## Documentation

- [Reference](docs/reference.md)
- [Contributing](CONTRIBUTING.md)
- [Agent Guidance](AGENTS.md)
