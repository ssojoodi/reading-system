from django.conf import settings
from django.db import models
from django.urls import reverse


class Book(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
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


class BookChunk(models.Model):
    book = models.ForeignKey(Book, related_name="chunks", on_delete=models.CASCADE)
    index = models.PositiveIntegerField()
    text = models.TextField()
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
