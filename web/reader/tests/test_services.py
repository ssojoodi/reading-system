from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from reader.models import Book, BookChunk, UserBookProgress
from reader.services import (
    move_progress,
    regenerate_book_chunks,
    split_text_into_chunks,
    start_book_for_user,
)


class ChunkingTests(TestCase):
    def test_split_text_into_chunks_extends_to_paragraph_boundary(self):
        text = "First paragraph line one.\nStill first paragraph.\n\nSecond paragraph."

        chunks = split_text_into_chunks(text, chunk_size=10)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, "First paragraph line one.\nStill first paragraph.")
        self.assertEqual(chunks[0].start_line, 0)
        self.assertEqual(chunks[0].end_line, 2)
        self.assertEqual(chunks[1].text, "Second paragraph.")

    def test_regenerate_book_chunks_replaces_existing_chunks(self):
        book = Book.objects.create(
            slug="test-book",
            title="Test Book",
            full_text="Alpha paragraph.\n\nBeta paragraph.",
            chunk_size=10,
        )

        regenerate_book_chunks(book)
        first_count = book.chunks.count()
        book.full_text = "Gamma paragraph only."
        book.save()
        regenerate_book_chunks(book)

        self.assertEqual(first_count, 2)
        self.assertEqual(book.chunks.count(), 1)
        self.assertEqual(book.chunks.first().text, "Gamma paragraph only.")
        self.assertEqual(book.chunks.first().notes, "")

    def test_regenerate_book_chunks_rejects_finalized_books(self):
        book = Book.objects.create(
            slug="finalized-book",
            title="Finalized Book",
            full_text="Alpha paragraph.",
            chunk_size=10,
        )
        regenerate_book_chunks(book)
        book.status = Book.Status.FINALIZED
        book.save()

        with self.assertRaises(ValidationError):
            regenerate_book_chunks(book)

    def test_finalized_book_chunks_cannot_be_added_edited_or_deleted(self):
        book = Book.objects.create(
            slug="locked-book",
            title="Locked Book",
            full_text="Alpha paragraph.",
            chunk_size=10,
        )
        regenerate_book_chunks(book)
        chunk = book.chunks.first()
        book.status = Book.Status.FINALIZED
        book.save()

        with self.assertRaises(ValidationError):
            BookChunk.objects.create(
                book=book,
                index=1,
                text="New chunk.",
                start_line=1,
                end_line=2,
                char_count=10,
            )

        chunk.text = "Edited chunk."
        with self.assertRaises(ValidationError):
            chunk.save()

        with self.assertRaises(ValidationError):
            chunk.delete()

        with self.assertRaises(ValidationError):
            BookChunk.objects.filter(id=chunk.id).delete()


class ProgressTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="reader", password="password"
        )
        self.other_user = self.user_model.objects.create_user(
            username="other", password="password"
        )
        self.book = Book.objects.create(
            slug="progress-book",
            title="Progress Book",
            full_text="One.\n\nTwo.\n\nThree.",
            chunk_size=4,
        )
        regenerate_book_chunks(self.book)

    def test_start_book_creates_progress_at_first_chunk(self):
        progress = start_book_for_user(self.book, self.user)

        self.assertEqual(progress.current_chunk.index, 0)
        self.assertEqual(UserBookProgress.objects.count(), 1)

    def test_user_progress_is_independent(self):
        first_progress = start_book_for_user(self.book, self.user)
        second_progress = start_book_for_user(self.book, self.other_user)

        move_progress(first_progress, "next")
        second_progress.refresh_from_db()

        self.assertEqual(first_progress.current_chunk.index, 1)
        self.assertEqual(second_progress.current_chunk.index, 0)

    def test_previous_and_next_navigation_stays_within_book_bounds(self):
        progress = start_book_for_user(self.book, self.user)

        move_progress(progress, "previous")
        self.assertEqual(progress.current_chunk.index, 0)

        move_progress(progress, "next")
        self.assertEqual(progress.current_chunk.index, 1)

        move_progress(progress, "next")
        move_progress(progress, "next")
        self.assertEqual(progress.current_chunk.index, 2)
