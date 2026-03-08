# AGENTS.md

## Purpose

This repository contains a reading system that:

- reads books from plain-text files in `books/library/`
- tracks per-book progress in JSON in `books/reading/`
- generates an interpreted reading chunk through an OpenAI-compatible API
- Emails the latest reading as an HTML email

## Canonical Entry Points

- `read-book.py` - primary CLI for `start`, `next`, and `status`
- `setup.sh` - creates the expected working directory structure
- `send-daily.sh` - default Mailgun-based delivery script

## Key Directories

- `books/library/` - source text files
- `books/reading/` - active per-book state files, created automatically by `start` when missing
- `books/finished/` - completed books and future notes
- `books/summaries/` - reserved for recap/summaries
- `output_files/` - generated HTML artifacts; do not commit
- `docs/` - public documentation
- `deploy/` - secret and specific deployment files

## Editing Rules

- Document every new environment variable in `.env.example`.
- Keep CLI examples in `README.md` current with the code.
- Prefer generic configuration over personal infrastructure values.

## Validation Expectations

For changes to the reading system:

```bash
uv run python read-book.py status
uv run python read-book.py start art-of-war --line 1
uv run python read-book.py next art-of-war
```

For changes to delivery flow:

```bash
./send-daily.sh --dry-run
```

## Open-Source Boundary

This repository should be documented as:

- a CLI reading system
- integrated with LLM backends
- integrated with email delivery and scheduling

This repository should not assume:

- a plain vanilla linux server
- a specific recipient list for email delivery
