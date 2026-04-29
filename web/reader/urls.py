from django.urls import path

from . import views

app_name = "reader"

urlpatterns = [
    path("", views.book_list, name="book_list"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
    path("books/<slug:slug>/start/", views.start_book, name="start_book"),
    path("books/<slug:slug>/read/", views.read_book, name="read_book"),
    path("books/<slug:slug>/jump/", views.jump_to_chunk, name="jump_to_chunk"),
    path(
        "books/<slug:slug>/chunks/<int:chunk_id>/",
        views.read_chunk,
        name="read_chunk",
    ),
    path(
        "books/<slug:slug>/read/<str:direction>/",
        views.move_between_chunks,
        name="move_between_chunks",
    ),
]
