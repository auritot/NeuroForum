from django.urls import path
from . import views

from .processes import user_process, post_process, comment_process

# from mailsender import views

urlpatterns = [
    # MARK: To Views
    path("", views.index, name="index"),
    path("login", views.login_view, name="login_view"),
    path("register", views.register_view, name="register_view"),
    path("create_post", views.create_post_view, name="create_post_view"),
    path("post/<int:post_id>", views.post_view, name="post_view"),
    path("mail_template", views.mail_template, name="mail_template"),
    path("chat/<str:other_user>/", views.chat_view, name="chat_view"),
    # MARK: Process
    path("login/submit", user_process.process_login, name="process_login"),
    path("register/submit", user_process.process_register, name="process_register"),
    path(
        "create_post/submit_post",
        post_process.process_create_post,
        name="process_create_post",
    ),
    path(
        "post/<int:post_id>/submit_comment",
        comment_process.process_create_comment,
        name="process_create_comment",
    ),
]
