from dataclasses import dataclass

from django.db import transaction

from .models import Book, BookChunk, UserBookProgress

DEFAULT_CHUNK_SIZE = 800


@dataclass(frozen=True)
class ChunkSpec:
    index: int
    text: str
    start_line: int
    end_line: int
    char_count: int


def split_text_into_chunks(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE
) -> list[ChunkSpec]:
    lines = text.splitlines()
    chunks: list[ChunkSpec] = []
    start = 0

    while start < len(lines):
        while start < len(lines) and not lines[start].strip():
            start += 1
        if start >= len(lines):
            break

        end = start
        char_count = 0
        while end < len(lines):
            char_count += len(lines[end]) + 1
            end += 1
            if char_count >= chunk_size:
                while end < len(lines) and lines[end].strip():
                    char_count += len(lines[end]) + 1
                    end += 1
                break

        chunk_end = end
        while end < len(lines) and not lines[end].strip():
            end += 1

        chunk_text = "\n".join(lines[start:chunk_end]).strip()
        if chunk_text:
            chunks.append(
                ChunkSpec(
                    index=len(chunks),
                    text=chunk_text,
                    start_line=start,
                    end_line=chunk_end,
                    char_count=len(chunk_text),
                )
            )
        start = end

    return chunks


@transaction.atomic
def regenerate_book_chunks(book: Book) -> list[BookChunk]:
    chunks = split_text_into_chunks(book.full_text, book.chunk_size)
    book.chunks.all().delete()
    created_chunks = [
        BookChunk(
            book=book,
            index=chunk.index,
            text=chunk.text,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            char_count=chunk.char_count,
        )
        for chunk in chunks
    ]
    BookChunk.objects.bulk_create(created_chunks)
    book.total_lines = len(book.full_text.splitlines())
    book.save(update_fields=["total_lines", "updated_at"])

    first_chunk = book.chunks.order_by("index").first()
    if first_chunk is None:
        book.reader_progress.update(current_chunk=None)
    else:
        book.reader_progress.filter(current_chunk__isnull=True).update(
            current_chunk=first_chunk
        )
        stale_progress = book.reader_progress.exclude(current_chunk__book=book)
        stale_progress.update(current_chunk=first_chunk)
    return list(book.chunks.all())


@transaction.atomic
def start_book_for_user(book: Book, user) -> UserBookProgress:
    first_chunk = book.chunks.order_by("index").first()
    progress, created = UserBookProgress.objects.get_or_create(
        user=user,
        book=book,
        defaults={"current_chunk": first_chunk},
    )
    if created:
        return progress
    if progress.current_chunk is None and first_chunk is not None:
        progress.current_chunk = first_chunk
        progress.save(update_fields=["current_chunk", "last_read_at"])
    return progress


def move_progress(progress: UserBookProgress, direction: str) -> UserBookProgress:
    if progress.current_chunk is None:
        first_chunk = progress.book.chunks.order_by("index").first()
        if first_chunk is not None:
            progress.current_chunk = first_chunk
            progress.save(update_fields=["current_chunk", "last_read_at"])
        return progress

    if direction == "next":
        target = (
            progress.book.chunks.filter(index__gt=progress.current_chunk.index)
            .order_by("index")
            .first()
        )
    elif direction == "previous":
        target = (
            progress.book.chunks.filter(index__lt=progress.current_chunk.index)
            .order_by("-index")
            .first()
        )
    else:
        raise ValueError(f"Unsupported direction: {direction}")

    if target is not None:
        progress.current_chunk = target
        progress.save(update_fields=["current_chunk", "last_read_at"])
    return progress


def set_progress_to_chunk(
    progress: UserBookProgress, chunk: BookChunk
) -> UserBookProgress:
    if chunk.book_id != progress.book_id:
        raise ValueError("Chunk does not belong to the progress book.")
    if progress.current_chunk_id != chunk.id:
        progress.current_chunk = chunk
        progress.save(update_fields=["current_chunk", "last_read_at"])
    return progress
