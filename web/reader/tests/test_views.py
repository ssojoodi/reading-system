from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reader.models import Book, UserBookProgress
from reader.services import regenerate_book_chunks


class ReaderViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader", password="password"
        )
        self.book = Book.objects.create(
            slug="view-book",
            title="View Book",
            author="Writer",
            full_text="First chunk.\n\nSecond chunk.",
            chunk_size=8,
        )
        regenerate_book_chunks(self.book)

    def test_anonymous_user_redirects_to_login(self):
        response = self.client.get(reverse("reader:book_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_logged_in_user_can_start_book(self):
        self.client.login(username="reader", password="password")
        first_chunk = self.book.chunks.get(index=0)

        response = self.client.post(reverse("reader:start_book", args=[self.book.slug]))

        self.assertRedirects(
            response,
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id]),
        )
        progress = UserBookProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.current_chunk.index, 0)

    def test_next_and_previous_update_current_user_progress(self):
        self.client.login(username="reader", password="password")
        self.client.post(reverse("reader:start_book", args=[self.book.slug]))

        self.client.post(
            reverse("reader:move_between_chunks", args=[self.book.slug, "next"])
        )
        progress = UserBookProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.current_chunk.index, 1)

        self.client.post(
            reverse("reader:move_between_chunks", args=[self.book.slug, "previous"])
        )
        progress.refresh_from_db()
        self.assertEqual(progress.current_chunk.index, 0)

    def test_read_view_renders_current_chunk(self):
        self.client.login(username="reader", password="password")
        first_chunk = self.book.chunks.get(index=0)

        response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id])
        )

        self.assertContains(response, "First chunk.")
        self.assertContains(response, "Chunk 1 of 2")

    def test_read_view_redirects_to_current_chunk_url(self):
        self.client.login(username="reader", password="password")
        first_chunk = self.book.chunks.get(index=0)

        response = self.client.get(reverse("reader:read_book", args=[self.book.slug]))

        self.assertRedirects(
            response,
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id]),
        )

    def test_direct_chunk_url_updates_user_progress(self):
        self.client.login(username="reader", password="password")
        second_chunk = self.book.chunks.get(index=1)

        response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, second_chunk.id])
        )

        self.assertContains(response, "Second chunk.")
        progress = UserBookProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.current_chunk, second_chunk)

    def test_jump_to_chunk_number_redirects_to_chunk_id_url(self):
        self.client.login(username="reader", password="password")
        second_chunk = self.book.chunks.get(index=1)

        response = self.client.post(
            reverse("reader:jump_to_chunk", args=[self.book.slug]),
            {"chunk_number": "2"},
        )

        self.assertRedirects(
            response,
            reverse("reader:read_chunk", args=[self.book.slug, second_chunk.id]),
        )
        progress = UserBookProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.current_chunk, second_chunk)
