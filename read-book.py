#!/usr/bin/env python3
"""
Book reader: books/ folder, progress in books/reading/<book_id>.json.
HTML output: output_files/ (or OUTPUT_DIR). Commands: next [book_id] | status | start <book_id>
Env: BOOKS_DIR, OUTPUT_DIR, OPENAI_API_KEY, OPENAI_BASE_URL (Ollama), READER_MODEL
"""

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_books_dir() -> Path:
    b = os.environ.get("BOOKS_DIR")
    return Path(b).resolve() if b else Path.cwd() / "books"


def get_output_dir() -> Path:
    o = os.environ.get("OUTPUT_DIR")
    return Path(o).resolve() if o else Path.cwd() / "output_files"


def _norm_path(p: str, books_dir: Path) -> Path:
    p = p.strip().replace("books/", "", 1).replace("books\\", "", 1)
    return books_dir / p


def load_state(book_id: str, books_dir: Path) -> dict:
    path = books_dir / "reading" / f"{book_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Book not found: {book_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(book_id: str, state: dict, books_dir: Path) -> None:
    path = books_dir / "reading" / f"{book_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _default_title(book_id: str) -> str:
    return re.sub(r"\s+", " ", book_id.replace("-", " ").replace("_", " ")).strip().title()


def ensure_state(book_id: str, books_dir: Path) -> tuple[dict, bool]:
    try:
        return load_state(book_id, books_dir), False
    except FileNotFoundError:
        book_path = books_dir / "library" / f"{book_id}.txt"
        if not book_path.exists():
            raise FileNotFoundError(f"Book not found: {book_id}")
        total_lines = len(book_path.read_text(encoding="utf-8", errors="replace").splitlines())
        state = {
            "bookId": book_id,
            "title": _default_title(book_id),
            "author": "",
            "filePath": f"books/library/{book_id}.txt",
            "startedAt": datetime.now(tz=timezone.utc).isoformat(),
            "status": "active",
            "progress": {
                "currentLine": 0,
                "totalLines": total_lines,
                "chunkSize": CHUNK_SIZE,
                "estimatedPosition": "0%",
            },
        }
        save_state(book_id, state, books_dir)
        return state, True


def get_active_book(books_dir: Path) -> Optional[dict]:
    r = books_dir / "reading"
    if not r.exists():
        return None
    active = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in r.glob("*.json")]
    active = [(p, s) for p, s in active if s.get("status") == "active"]
    return max(active, key=lambda x: x[0].stat().st_mtime)[1] if active else None


def _lines(book_id: str, books_dir: Path) -> tuple[list[str], dict, dict]:
    state = load_state(book_id, books_dir)
    path = _norm_path(state["filePath"], books_dir)
    if not path.exists():
        raise FileNotFoundError(f"Book file not found: {path}")
    return (
        path.read_text(encoding="utf-8", errors="replace").splitlines(),
        state,
        state.setdefault("progress", {}),
    )


CHUNK_SIZE = 800


def read_next_chunk(book_id: str, books_dir: Path) -> dict:
    lines, state, progress = _lines(book_id, books_dir)
    progress.setdefault("totalLines", len(lines))
    start, size = progress.get("currentLine", 0), progress.get("chunkSize", CHUNK_SIZE)
    # If we start on an empty line (e.g. after a chapter header), include the header
    while start > 0 and not lines[start].strip():
        start -= 1
    end, n = start, 0
    while end < len(lines):
        n += len(lines[end]) + 1
        end += 1
        if n >= size:
            while end < len(lines) and lines[end].strip():
                n += len(lines[end]) + 1
                end += 1
            break
    chunk_end = end
    while end < len(lines) and not lines[end].strip():
        end += 1
    chunk = "\n".join(lines[start:chunk_end])
    progress["currentLine"] = end
    progress["lastChunkStart"] = start
    progress["lastChunkEnd"] = chunk_end
    progress["lastChunkSent"] = datetime.now(tz=timezone.utc).isoformat()
    progress["estimatedPosition"] = f"{round(end / len(lines) * 100)}%"
    save_state(book_id, state, books_dir)
    return {
        "chunk": chunk.strip(),
        "progress": progress,
        "title": state["title"],
        "author": state.get("author", ""),
        "finished": end >= len(lines),
    }


def get_last_chunk(book_id: str, books_dir: Path) -> tuple[str, dict]:
    lines, state, progress = _lines(book_id, books_dir)
    cur = progress.get("currentLine", 0)
    if "lastChunkStart" in progress and "lastChunkEnd" in progress:
        start, chunk_end = progress["lastChunkStart"], progress["lastChunkEnd"]
        return "\n".join(lines[start:chunk_end]).strip(), state
    size = progress.get("chunkSize", CHUNK_SIZE)
    start, n = cur, 0
    while start > 0 and n < size:
        start -= 1
        n += len(lines[start]) + 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    chunk_end = cur
    while chunk_end > start and not lines[chunk_end - 1].strip():
        chunk_end -= 1
    return "\n".join(lines[start:chunk_end]).strip(), state


def show_status(books_dir: Path) -> list:
    r = books_dir / "reading"
    if not r.exists():
        return []
    out = []
    for p in sorted(r.glob("*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        prog = s.get("progress", {})
        out.append({"bookId": s.get("bookId"), "title": s.get("title"), "author": s.get("author", ""), "status": s.get("status"), "progress": prog.get("estimatedPosition"), "lastRead": prog.get("lastChunkSent")})
    return out


def get_interpretation(book_id: str, books_dir: Path) -> dict:
    chunk, state = get_last_chunk(book_id, books_dir)
    if not chunk:
        raise ValueError("No chunk. Run 'next' first.")
    title, author = state.get("title", "Unknown"), state.get("author", "")
    prompt = f'You are helping a modern professional understand a classic text.\n\nHere is a passage from "{title}" by {author}:\n\n---\n{chunk}\n---\n\nProvide a modern interpretation in exactly three parts. Be concise.\n**1. Plain-English Summary** — 2–3 sentences.\n**2. Modern Parallel** — Business/leadership equivalent today.\n**3. Apply It** — One concrete, actionable step this week (start with a verb).'
    r = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url=os.environ.get("OPENAI_BASE_URL")).chat.completions.create(
        model=os.environ.get("READER_MODEL"), messages=[{"role": "user", "content": prompt}], max_completion_tokens=1200
    )
    return {"title": title, "author": author, "progress": state.get("progress", {}), "chunk": chunk, "interpretation": r.choices[0].message.content}


def _interp_html(text: str) -> str:
    if not text:
        return ""
    out = []
    for p in [p.strip() for p in text.split("\n\n") if p.strip()]:
        p = re.sub(r"\*(.+?)\*", r"<em>\1</em>", re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(p)))
        out.append(f"        <p>{p}</p>")
    return "\n\n".join(out)


_CSS = """
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.7; max-width: 680px; margin: 40px auto; padding: 24px; color: #333; background: #fff; }
        .email-header { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
        h1 { color: #2c3e50; font-size: 26px; margin: 0 0 4px 0; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .meta { font-size: 12px; color: #95a5a6; margin-bottom: 4px; }
        .section-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #7f8c8d; margin: 24px 0 8px 0; }
        .original-text { background: #f8f9fa; border-left: 4px solid #3498db; padding: 16px 20px; font-family: Georgia, serif; font-size: 15px; line-height: 1.8; color: #2c3e50; border-radius: 0 4px 4px 0; margin: 8px 0 20px 0; white-space: pre-wrap; }
        .interpretation { background: #fdfefe; border-left: 4px solid #27ae60; padding: 16px 20px; font-size: 15px; line-height: 1.8; color: #333; border-radius: 0 4px 4px 0; margin: 8px 0 20px 0; }
        .interpretation p { margin: 0 0 1em 0; }
        .interpretation p:last-child { margin-bottom: 0; }
        .progress-bar { background: #ecf0f1; border-radius: 4px; height: 6px; margin: 6px 0 2px 0; overflow: hidden; }
        .progress-fill { background: #3498db; height: 100%; border-radius: 4px; }
        .progress-label { font-size: 12px; color: #95a5a6; }
        hr { border: none; border-top: 1px solid #ecf0f1; margin: 28px 0; }
        .email-footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #ecf0f1; font-size: 12px; color: #aaa; text-align: center; }
"""


def build_reading_html(
    *,
    title: str,
    author: str,
    chunk: str,
    interpretation: str,
    current_line: int,
    total_lines: int,
    pct: str,
) -> str:
    now = datetime.now(timezone.utc)
    date_str = f"{now.strftime('%A')} · {now.strftime('%B %d, %Y')} · Morning"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Reading — {html.escape(title)}</title>
    <style>{_CSS}</style>
</head>
<body>
    <div class="email-header">{date_str}</div>
    <h1>{html.escape(title)}</h1>
    <div class="meta">{html.escape(author)} &nbsp;·&nbsp; {pct} complete &nbsp;·&nbsp; Line {current_line:,} of {total_lines:,}</div>
    <div class="progress-bar"><div class="progress-fill" style="width:{pct}"></div></div>
    <div class="progress-label">{pct} through the book</div>
    <hr>
    <div class="section-label">📜 Original Text</div>
    <div class="original-text">{html.escape(chunk)}</div>
    <div class="section-label">💡 Interpretation</div>
    <div class="interpretation">
{_interp_html(interpretation)}
    </div>
    <div class="email-footer">Reading {html.escape(title)} by {html.escape(author)} &nbsp;·&nbsp; Line {current_line:,} of {total_lines:,}</div>
</body>
</html>"""


def main() -> None:
    books_dir = get_books_dir()
    parser = argparse.ArgumentParser(description="Book reader (books/ folder)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show progress")
    sub.add_parser("next", help="Next chunk + interpret → HTML").add_argument(
        "book_id", nargs="?", help="Book ID"
    )
    start_parser = sub.add_parser("start", help="Start book")
    start_parser.add_argument("book_id", help="Book ID")
    start_parser.add_argument(
        "--line", "-l", type=int, default=None, metavar="N",
        help="Start from line N (1-based)",
    )
    args = parser.parse_args()

    def book_id() -> str:
        bid = getattr(args, "book_id", None) or (get_active_book(books_dir) or {}).get("bookId")
        if not bid:
            print("No active book. Use: read-book.py start <book_id>", file=sys.stderr)
            sys.exit(1)
        return bid

    try:
        if args.command == "status":
            print(json.dumps(show_status(books_dir), indent=2))
            return
        if args.command == "start":
            s, created = ensure_state(args.book_id, books_dir)
            msg = f"Started: {s['title']}"
            if s.get("author"):
                msg += f" by {s['author']}"
            if getattr(args, "line", None) is not None:
                line = args.line
                if line < 1:
                    print("Error: --line must be >= 1", file=sys.stderr)
                    sys.exit(1)
                path = _norm_path(s["filePath"], books_dir)
                if not path.exists():
                    raise FileNotFoundError(f"Book file not found: {path}")
                total = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
                if line > total:
                    print(f"Error: --line {line} exceeds book length ({total} lines)", file=sys.stderr)
                    sys.exit(1)
                s.setdefault("progress", {})["currentLine"] = line - 1
                s["progress"]["totalLines"] = total
                s["progress"]["estimatedPosition"] = f"{round((line - 1) / total * 100)}%"
                save_state(args.book_id, s, books_dir)
                msg += f" from line {line}"
            if created:
                msg += " (created state file)"
            print(msg)
            return
        bid = book_id()
        chunk_result = read_next_chunk(bid, books_dir)
        if chunk_result["finished"]:
            print(json.dumps({"message": "Book finished", "title": chunk_result["title"], "progress": chunk_result["progress"]}, indent=2))
            return
        interp = get_interpretation(bid, books_dir)
        prog = interp["progress"]
        out_dir = get_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{bid}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.html"
        out_path.write_text(
            build_reading_html(
                title=interp["title"],
                author=interp["author"],
                chunk=interp["chunk"],
                interpretation=interp["interpretation"],
                current_line=prog.get("currentLine", 0),
                total_lines=prog.get("totalLines", 0),
                pct=prog.get("estimatedPosition", "0%"),
            ),
            encoding="utf-8",
        )
        print(json.dumps({"output": str(out_path.resolve()), "progress": prog}, indent=2))
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
