from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from reader.admin import BookAdminForm
from reader.models import Book


class BookAdminFormTests(TestCase):
    def test_text_file_upload_replaces_full_text(self):
        form = BookAdminForm(
            data={
                "slug": "uploaded-book",
                "title": "Uploaded Book",
                "author": "",
                "status": "new",
                "chunk_size": 800,
                "full_text": "",
            },
            files={
                "text_file": SimpleUploadedFile(
                    "book.txt", b"Uploaded text.", content_type="text/plain"
                )
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["full_text"], "Uploaded text.")

    def test_thumbnail_upload_is_encoded_for_database_storage(self):
        form = BookAdminForm(
            data={
                "slug": "covered-book",
                "title": "Covered Book",
                "author": "",
                "status": "new",
                "chunk_size": 800,
                "full_text": "Text.",
            },
            files={
                "thumbnail_file": SimpleUploadedFile(
                    "cover.gif", b"GIF89a", content_type="image/gif"
                )
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["thumbnail_content_type"], "image/gif")
        self.assertEqual(form.cleaned_data["thumbnail_data"], "R0lGODlh")

    def test_thumbnail_data_url_returns_embedded_image_url(self):
        book = Book(
            slug="covered-book",
            title="Covered Book",
            thumbnail_content_type="image/gif",
            thumbnail_data="R0lGODlh",
            full_text="Text.",
        )

        self.assertEqual(book.thumbnail_data_url, "data:image/gif;base64,R0lGODlh")
