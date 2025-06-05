from django.urls import path
from . import views

from .processes import user_process, post_process, comment_process

# from mailsender import views

urlpatterns = [
    # MARK: To Views
    path("", views.index, name="index"),
    path("login", views.login_view, name="login_view"),
    path("register", views.register_view, name="register_view"),
    path("create_post", views.post_form_view, name="create_post_view"),
    path("edit_post/<int:post_id>", views.post_form_view, name="edit_post_view"),
    path("post/<int:post_id>", views.post_view, name="post_view"),
    # User Related Pages
    path("profile", views.user_profile_view, name="user_profile_view"),
    path("manage_post", views.user_manage_post_view, name="user_manage_post_view"),
    path("manage_comment", views.user_manage_comment_view, name="user_manage_comment_view"),
    path("mail_template", views.mail_template, name="mail_template"),
    path("chat/<str:other_user>/", views.chat_view, name="chat_view"),
    # MARK: Process
    # User Related
    path("login/authenticate", user_process.process_login, name="process_login"),
    path("register/registration", user_process.process_register, name="process_register"),
    # Post Related
    path("post/create", post_process.process_create_post, name="process_create_post"),
    path("post/delete/<int:post_id>", post_process.process_delete_post, name="process_delete_post"),
    path("post/update/<int:post_id>", post_process.process_update_post, name="process_update_post"),
    # Comment Related
    path("comment/create/<int:post_id>", comment_process.process_create_comment, name="process_create_comment"),
    path("comment/delete/<int:post_id>/<int:comment_id>", comment_process.process_delete_comment, name="process_delete_comment"),
    path("comment/update/<int:post_id>/<int:comment_id>", comment_process.process_update_comment, name="process_update_comment"),
]
