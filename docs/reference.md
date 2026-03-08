# Reference

## Flow

1. Put a plain-text book at `books/library/<book_id>.txt`.
2. Run `uv run python read-book.py start <book_id>`.
3. Run `uv run python read-book.py next [book_id]`.
4. Optionally run `./send-daily.sh`.

`start` creates `books/reading/<book_id>.json` automatically if it does not exist.

## Commands

```bash
uv run python read-book.py start <book_id>
uv run python read-book.py start <book_id> --line 120
uv run python read-book.py next [book_id]
uv run python read-book.py status
```

## Files

- `books/library/`: source `.txt` books
- `books/reading/`: per-book state JSON
- `output_files/`: generated HTML output

## State Shape

```json
{
  "bookId": "art-of-war",
  "title": "The Art of War",
  "author": "Sun Tzu (translated by Lionel Giles)",
  "filePath": "books/library/art-of-war.txt",
  "startedAt": "2026-02-14T14:10:00.000Z",
  "status": "active",
  "progress": {
    "currentLine": 0,
    "totalLines": 7137,
    "chunkSize": 800,
    "estimatedPosition": "0%"
  }
}
```

Auto-created state files derive `title` from `book_id` and leave `author` blank.

## Notes

- `currentLine` is zero-based.
- `--line N` on `start` is one-based.
- `next` uses the active book if `book_id` is omitted.
- Source books are currently expected to be `.txt` files.
