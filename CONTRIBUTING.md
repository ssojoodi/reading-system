# Contributing

## Setup

```bash
uv venv
uv pip install -r requirements.txt
./setup.sh
```

## Local Checks

```bash
uv run python read-book.py status
uv run python read-book.py start art-of-war --line 1
./send-daily.sh --dry-run
```

## Notes

- use `uv` for local Python commands
- keep config documented in `.env.example`
- avoid committing local secrets, generated output, or deployment-specific values
