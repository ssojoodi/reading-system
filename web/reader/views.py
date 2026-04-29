from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Book, BookChunk, UserBookProgress
from .services import set_progress_to_chunk, start_book_for_user


@login_required
def book_list(request):
    books = Book.objects.prefetch_related("chunks").all()
    progress_by_book = {
        progress.book_id: progress
        for progress in UserBookProgress.objects.filter(user=request.user).select_related(
            "book", "current_chunk"
        )
    }
    book_items = [
        {"book": book, "progress": progress_by_book.get(book.id)}
        for book in books
    ]
    return render(request, "reader/book_list.html", {"book_items": book_items})


@login_required
def book_detail(request, slug):
    book = get_object_or_404(Book.objects.prefetch_related("chunks"), slug=slug)
    progress = UserBookProgress.objects.filter(user=request.user, book=book).first()
    return render(
        request,
        "reader/book_detail.html",
        {"book": book, "progress": progress},
    )


@login_required
@require_POST
def start_book(request, slug):
    book = get_object_or_404(Book, slug=slug)
    progress = start_book_for_user(book, request.user)
    if progress.current_chunk is None:
        return redirect("reader:read_book", slug=book.slug)
    return redirect("reader:read_chunk", slug=book.slug, chunk_id=progress.current_chunk_id)


@login_required
def read_book(request, slug):
    book = get_object_or_404(Book, slug=slug)
    progress = start_book_for_user(book, request.user)
    current_chunk = progress.current_chunk
    if current_chunk is not None:
        return redirect("reader:read_chunk", slug=book.slug, chunk_id=current_chunk.id)
    total_chunks = book.chunks.count()
    return render(
        request,
        "reader/read_book.html",
        {
            "book": book,
            "progress": progress,
            "current_chunk": current_chunk,
            "previous_chunk": None,
            "next_chunk": None,
            "total_chunks": total_chunks,
            "can_go_previous": False,
            "can_go_next": False,
            "percent_complete": 0,
        },
    )


@login_required
def read_chunk(request, slug, chunk_id):
    book = get_object_or_404(Book, slug=slug)
    current_chunk = get_object_or_404(BookChunk, id=chunk_id, book=book)
    progress = start_book_for_user(book, request.user)
    set_progress_to_chunk(progress, current_chunk)
    total_chunks = book.chunks.count()
    previous_chunk = (
        book.chunks.filter(index__lt=current_chunk.index).order_by("-index").first()
    )
    next_chunk = book.chunks.filter(index__gt=current_chunk.index).order_by("index").first()
    can_go_previous = bool(current_chunk and current_chunk.index > 0)
    can_go_next = bool(current_chunk and current_chunk.index < total_chunks - 1)
    percent_complete = progress.percent_complete
    return render(
        request,
        "reader/read_book.html",
        {
            "book": book,
            "progress": progress,
            "current_chunk": current_chunk,
            "previous_chunk": previous_chunk,
            "next_chunk": next_chunk,
            "total_chunks": total_chunks,
            "can_go_previous": can_go_previous,
            "can_go_next": can_go_next,
            "percent_complete": percent_complete,
        },
    )


@login_required
@require_POST
def jump_to_chunk(request, slug):
    book = get_object_or_404(Book, slug=slug)
    raw_chunk_number = request.POST.get("chunk_number", "")
    try:
        chunk_number = int(raw_chunk_number)
    except ValueError:
        return redirect("reader:read_book", slug=book.slug)

    target = book.chunks.filter(index=chunk_number - 1).first()
    if target is None:
        return redirect("reader:read_book", slug=book.slug)

    progress = start_book_for_user(book, request.user)
    set_progress_to_chunk(progress, target)
    return redirect("reader:read_chunk", slug=book.slug, chunk_id=target.id)
