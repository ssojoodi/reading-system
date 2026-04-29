from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from reader.admin import BookAdminForm


class BookAdminFormTests(TestCase):
    def test_text_file_upload_replaces_full_text(self):
        form = BookAdminForm(
            data={
                "slug": "uploaded-book",
                "title": "Uploaded Book",
                "author": "",
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
