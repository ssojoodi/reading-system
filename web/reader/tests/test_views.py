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
        self.book.status = Book.Status.FINALIZED
        self.book.save()

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

    def test_next_and_previous_links_use_chunk_urls(self):
        self.client.login(username="reader", password="password")
        first_chunk = self.book.chunks.get(index=0)
        second_chunk = self.book.chunks.get(index=1)

        first_response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id])
        )
        self.assertContains(
            first_response,
            reverse("reader:read_chunk", args=[self.book.slug, second_chunk.id]),
        )

        second_response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, second_chunk.id])
        )
        self.assertContains(
            second_response,
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id]),
        )
        progress = UserBookProgress.objects.get(user=self.user, book=self.book)
        progress.refresh_from_db()
        self.assertEqual(progress.current_chunk.index, 1)

    def test_read_view_renders_current_chunk(self):
        self.client.login(username="reader", password="password")
        first_chunk = self.book.chunks.get(index=0)

        response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id])
        )

        self.assertContains(response, "First chunk.")
        self.assertContains(response, "Chunk 1 of 2")
        self.assertNotContains(response, "Notes")

    def test_read_view_renders_notes_when_notes_exist(self):
        self.client.login(username="reader", password="password")
        self.book.status = Book.Status.INTERPRETED
        self.book.save()
        first_chunk = self.book.chunks.get(index=0)
        first_chunk.notes = "A useful note.\nWith a second line."
        first_chunk.save()
        self.book.status = Book.Status.FINALIZED
        self.book.save()

        response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id])
        )

        self.assertContains(response, "Notes")
        self.assertContains(response, "A useful note.")
        self.assertContains(response, "With a second line.")

    def test_read_view_allows_simple_note_html(self):
        self.client.login(username="reader", password="password")
        self.book.status = Book.Status.INTERPRETED
        self.book.save()
        first_chunk = self.book.chunks.get(index=0)
        first_chunk.notes = (
            "A <strong>strong</strong>, <b>bold</b>, "
            "<em>emphasized</em>, and <i>italic</i> note."
        )
        first_chunk.save()
        self.book.status = Book.Status.FINALIZED
        self.book.save()

        response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id])
        )

        self.assertContains(response, "<strong>strong</strong>", html=True)
        self.assertContains(response, "<b>bold</b>", html=True)
        self.assertContains(response, "<em>emphasized</em>", html=True)
        self.assertContains(response, "<i>italic</i>", html=True)

    def test_read_view_strips_unsafe_note_html(self):
        self.client.login(username="reader", password="password")
        self.book.status = Book.Status.INTERPRETED
        self.book.save()
        first_chunk = self.book.chunks.get(index=0)
        first_chunk.notes = (
            '<strong onclick="alert(1)">safe text</strong>'
            '<script>alert("bad")</script>'
            '<a href="https://example.com">link text</a>'
        )
        first_chunk.save()
        self.book.status = Book.Status.FINALIZED
        self.book.save()

        response = self.client.get(
            reverse("reader:read_chunk", args=[self.book.slug, first_chunk.id])
        )

        self.assertContains(response, "<strong>safe text</strong>", html=True)
        self.assertNotContains(response, "onclick")
        self.assertNotContains(response, "<script")
        self.assertNotContains(response, 'href="https://example.com"')
        self.assertContains(response, "link text")

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

    def test_book_list_hides_non_finalized_books(self):
        Book.objects.create(
            slug="draft-book",
            title="Draft Book",
            status=Book.Status.CHUNKED,
            full_text="Draft text.",
        )
        self.client.login(username="reader", password="password")

        response = self.client.get(reverse("reader:book_list"))

        self.assertContains(response, "View Book")
        self.assertNotContains(response, "Draft Book")

    def test_non_finalized_book_detail_404s(self):
        draft = Book.objects.create(
            slug="draft-book",
            title="Draft Book",
            status=Book.Status.NEW,
            full_text="Draft text.",
        )
        self.client.login(username="reader", password="password")

        response = self.client.get(reverse("reader:book_detail", args=[draft.slug]))

        self.assertEqual(response.status_code, 404)
