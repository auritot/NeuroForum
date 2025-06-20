from django.urls import path
from . import views

from .processes import user_process, post_process, comment_process
from django.views.generic.base import RedirectView

# from mailsender import views

urlpatterns = [
    # MARK: To Views
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login_view"),
    path("login", RedirectView.as_view(url="/login/", permanent=True)),
    path("register", views.register_view, name="register_view"),
    path("create_post", views.post_form_view, name="create_post_view"),
    path("api/filtered-words/", views.filtered_words_api,
         name="filtered_words_api"),
    path("edit_post/<int:post_id>", views.post_form_view, name="edit_post_view"),
    path("post/<int:post_id>", views.post_view, name="post_view"),
    # User Related Pages
    path("profile", views.user_profile_view, name="user_profile_view"),
    path("manage_post", views.user_manage_post_view,
         name="user_manage_post_view"),
    path("manage_comment", views.user_manage_comment_view,
         name="user_manage_comment_view"),
    path("email_verification/", views.email_verification,
         name="email_verification"),
    path("chat/", views.chat_home_view, name="chat_home_view"),
    path("chat/start/", views.start_chat_view, name="start_chat"),
    path("chat/landing/", views.chat_landing_or_redirect_view, name="chat_landing"),
    path("chat/<str:other_user>/", views.chat_view, name="chat_view"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password_view"),
    path("reset_password/", views.reset_password_view, name="reset_password_view"),
    # MARK: Process
    # User Related
    path("login/authenticate", user_process.process_login, name="process_login"),
    path("register/registration", user_process.process_register,
         name="process_register"),
    path("user/update_profile", user_process.process_update_profile,
         name="process_update_profile"),
    path("user/change_password", user_process.process_change_password,
         name="process_change_password"),
    path('logout/', views.logout_view, name='logout_view'),
    # Post Related
    path("post/create", post_process.process_create_post,
         name="process_create_post"),
    path("post/delete/<int:post_id>",
         post_process.process_delete_post, name="process_delete_post"),
    path("post/update/<int:post_id>",
         post_process.process_update_post, name="process_update_post"),
    # Comment Related
    path("comment/create/<int:post_id>",
         comment_process.process_create_comment, name="process_create_comment"),
    path("comment/delete/<int:post_id>/<int:comment_id>",
         comment_process.process_delete_comment, name="process_delete_comment"),
    path("comment/update/<int:post_id>/<int:comment_id>",
         comment_process.process_update_comment, name="process_update_comment"),
    # Word Filter Related
    path("wordfilter/manage", views.manage_filtered_words_view,
         name="manage_wordfilter"),
    # Admin portal to Manage Users
    path("admin_portal/", views.admin_portal, name="admin_portal"),
    path("admin_portal/change-role/<int:user_id>/",
         views.change_user_role, name="change_user_role"),
    path("admin_portal/delete/<int:user_id>/",
         views.delete_user, name="delete_user"),
    path("admin_manage_posts/", views.admin_manage_post_view, name="admin_manage_post_view"),
    path("admin_manage_comments/", views.admin_manage_comment_view, name="admin_manage_comment_view"),
]
