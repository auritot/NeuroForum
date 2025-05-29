from django.urls import path
from . import views

urlpatterns = [
    # MARK: To Views
    path("", views.index, name="index"),
    path("login", views.login_view, name="login_view"),
    path("register", views.register_view, name="register_view"),
    path("create_post", views.create_post_view, name="create_post_view"),
    path("post/<int:post_id>", views.post_view, name="post_view"),
]
