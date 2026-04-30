# Generated manually for the separated Django reader app.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=255)),
                ("author", models.CharField(blank=True, max_length=255)),
                ("full_text", models.TextField()),
                ("total_lines", models.PositiveIntegerField(default=0)),
                ("chunk_size", models.PositiveIntegerField(default=800)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["title", "slug"],
            },
        ),
        migrations.CreateModel(
            name="BookChunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("index", models.PositiveIntegerField()),
                ("text", models.TextField()),
                ("start_line", models.PositiveIntegerField()),
                ("end_line", models.PositiveIntegerField()),
                ("char_count", models.PositiveIntegerField()),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="reader.book",
                    ),
                ),
            ],
            options={
                "ordering": ["book", "index"],
            },
        ),
        migrations.CreateModel(
            name="UserBookProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("last_read_at", models.DateTimeField(auto_now=True)),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reader_progress",
                        to="reader.book",
                    ),
                ),
                (
                    "current_chunk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="current_for_users",
                        to="reader.bookchunk",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reading_progress",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user", "book"],
            },
        ),
        migrations.AddConstraint(
            model_name="bookchunk",
            constraint=models.UniqueConstraint(
                fields=("book", "index"), name="unique_chunk_index_per_book"
            ),
        ),
        migrations.AddConstraint(
            model_name="userbookprogress",
            constraint=models.UniqueConstraint(
                fields=("user", "book"), name="unique_progress_per_user_book"
            ),
        ),
    ]
