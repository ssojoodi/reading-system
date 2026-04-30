from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse


class Book(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CHUNKED = "chunked", "Chunked"
        INTERPRETED = "interpreted", "Interpreted"
        FINALIZED = "finalized", "Finalized"

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    thumbnail_content_type = models.CharField(max_length=100, blank=True)
    thumbnail_data = models.TextField(blank=True)
    full_text = models.TextField()
    total_lines = models.PositiveIntegerField(default=0)
    chunk_size = models.PositiveIntegerField(default=800)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "slug"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("reader:book_detail", kwargs={"slug": self.slug})

    @property
    def is_in_catalog(self) -> bool:
        return self.status == self.Status.FINALIZED

    @property
    def thumbnail_data_url(self) -> str:
        if not self.thumbnail_data or not self.thumbnail_content_type:
            return ""
        return f"data:{self.thumbnail_content_type};base64,{self.thumbnail_data}"


class BookChunk(models.Model):
    book = models.ForeignKey(Book, related_name="chunks", on_delete=models.CASCADE)
    index = models.PositiveIntegerField()
    text = models.TextField()
    notes = models.TextField(blank=True)
    start_line = models.PositiveIntegerField()
    end_line = models.PositiveIntegerField()
    char_count = models.PositiveIntegerField()

    class Meta:
        ordering = ["book", "index"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "index"], name="unique_chunk_index_per_book"
            )
        ]

    def __str__(self) -> str:
        return f"{self.book} chunk {self.index + 1}"

    def clean(self):
        super().clean()
        if self.book_id and self.book.status == Book.Status.FINALIZED:
            raise ValidationError(
                "Book chunks cannot be added, edited, or deleted for finalized books."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.book_id and self.book.status == Book.Status.FINALIZED:
            raise ValidationError(
                "Book chunks cannot be added, edited, or deleted for finalized books."
            )
        return super().delete(*args, **kwargs)


class UserBookProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reading_progress",
        on_delete=models.CASCADE,
    )
    book = models.ForeignKey(
        Book,
        related_name="reader_progress",
        on_delete=models.CASCADE,
    )
    current_chunk = models.ForeignKey(
        BookChunk,
        related_name="current_for_users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user", "book"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"], name="unique_progress_per_user_book"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} reading {self.book}"

    @property
    def percent_complete(self) -> int:
        total = self.book.chunks.count()
        if not total or self.current_chunk is None:
            return 0
        return round(((self.current_chunk.index + 1) / total) * 100)


@receiver(pre_delete, sender=BookChunk)
def prevent_finalized_book_chunk_delete(sender, instance, **kwargs):
    if instance.book_id and instance.book.status == Book.Status.FINALIZED:
        raise ValidationError(
            "Book chunks cannot be added, edited, or deleted for finalized books."
        )
