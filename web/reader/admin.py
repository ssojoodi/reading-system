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

    class Meta:
        model = Book
        fields = ["slug", "title", "author", "chunk_size", "full_text", "text_file"]

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
        return cleaned_data


class BookChunkInline(admin.TabularInline):
    model = BookChunk
    fields = ["index", "start_line", "end_line", "char_count", "has_notes"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="Notes")
    def has_notes(self, obj):
        return bool(obj.notes.strip())


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookAdminForm
    list_display = ["title", "author", "slug", "chunk_count", "total_lines", "updated_at"]
    search_fields = ["title", "author", "slug"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [BookChunkInline]

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
    readonly_fields = ["book", "index", "text", "start_line", "end_line", "char_count"]
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


@admin.register(UserBookProgress)
class UserBookProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "current_chunk", "last_read_at"]
    list_filter = ["book", "last_read_at"]
    search_fields = ["user__username", "book__title"]
