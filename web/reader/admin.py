import base64

from django import forms
from django.contrib import admin

from .models import Book, BookChunk, UserBookProgress
from .services import regenerate_book_chunks


class BookAdminForm(forms.ModelForm):
    full_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 18}),
    )
    text_file = forms.FileField(
        required=False,
        help_text="Optional .txt upload. If provided, it replaces the full text.",
    )
    thumbnail_file = forms.FileField(
        required=False,
        help_text="Optional cover image. Stored in the database for simple deployment.",
    )

    class Meta:
        model = Book
        fields = [
            "slug",
            "title",
            "author",
            "status",
            "thumbnail_file",
            "thumbnail_content_type",
            "thumbnail_data",
            "chunk_size",
            "full_text",
            "text_file",
        ]
        widgets = {
            "thumbnail_data": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_thumbnail_file(self):
        uploaded_file = self.cleaned_data.get("thumbnail_file")
        if uploaded_file is None:
            return None
        if not uploaded_file.content_type.startswith("image/"):
            raise forms.ValidationError("Uploaded covers must be image files.")
        return {
            "content_type": uploaded_file.content_type,
            "data": base64.b64encode(uploaded_file.read()).decode("ascii"),
        }

    def clean_text_file(self):
        uploaded_file = self.cleaned_data.get("text_file")
        if uploaded_file is None:
            return None
        try:
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise forms.ValidationError("Uploaded books must be UTF-8 text files.") from exc

    def clean(self):
        cleaned_data = super().clean()
        uploaded_text = cleaned_data.get("text_file")
        full_text = cleaned_data.get("full_text")
        if uploaded_text:
            cleaned_data["full_text"] = uploaded_text
        elif not full_text:
            raise forms.ValidationError("Provide full text or upload a .txt file.")
        uploaded_thumbnail = cleaned_data.get("thumbnail_file")
        if uploaded_thumbnail:
            cleaned_data["thumbnail_content_type"] = uploaded_thumbnail["content_type"]
            cleaned_data["thumbnail_data"] = uploaded_thumbnail["data"]
        return cleaned_data


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookAdminForm
    list_display = [
        "title",
        "author",
        "slug",
        "status",
        "has_thumbnail",
        "chunk_count",
        "total_lines",
        "updated_at",
    ]
    list_filter = ["status"]
    search_fields = ["title", "author", "slug"]
    prepopulated_fields = {"slug": ("title",)}

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = Book.objects.get(pk=obj.pk)

        super().save_model(request, obj, form, change)

        should_regenerate = (
            not change
            or form.cleaned_data.get("text_file")
            or previous is None
            or previous.full_text != obj.full_text
            or previous.chunk_size != obj.chunk_size
        )
        if should_regenerate:
            regenerate_book_chunks(obj)

    @admin.display(description="Chunks")
    def chunk_count(self, obj):
        return obj.chunks.count()

    @admin.display(boolean=True, description="Cover")
    def has_thumbnail(self, obj):
        return bool(obj.thumbnail_data and obj.thumbnail_content_type)


@admin.register(BookChunk)
class BookChunkAdmin(admin.ModelAdmin):
    list_display = [
        "book",
        "display_index",
        "start_line",
        "end_line",
        "char_count",
        "has_notes",
    ]
    list_filter = ["book"]
    search_fields = ["book__title", "text", "notes"]
    readonly_fields = ["start_line", "end_line", "char_count"]
    fields = [
        "book",
        "index",
        "text",
        "notes",
        "start_line",
        "end_line",
        "char_count",
    ]

    @admin.display(description="Chunk")
    def display_index(self, obj):
        return obj.index + 1

    @admin.display(boolean=True, description="Notes")
    def has_notes(self, obj):
        return bool(obj.notes.strip())

    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        has_permission = super().has_change_permission(request, obj)
        if obj is None:
            return has_permission
        return has_permission and obj.book.status != Book.Status.FINALIZED

    def has_delete_permission(self, request, obj=None):
        has_permission = super().has_delete_permission(request, obj)
        if obj is None:
            return has_permission
        return has_permission and obj.book.status != Book.Status.FINALIZED

    def delete_queryset(self, request, queryset):
        editable_queryset = queryset.exclude(book__status=Book.Status.FINALIZED)
        return super().delete_queryset(request, editable_queryset)


@admin.register(UserBookProgress)
class UserBookProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "current_chunk", "last_read_at"]
    list_filter = ["book", "last_read_at"]
    search_fields = ["user__username", "book__title"]
