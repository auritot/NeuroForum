from django.views.decorators.clickjacking import xframe_options_exempt
from .models import ChatRoom, UserAccount
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse  # Added for reversing URLs
from urllib.parse import urlencode  # Added for encoding query parameters
from django.views.decorators.http import require_POST
from .services import session_utils, utilities
from .services.db_services import user_service, post_service, comment_service, log_service
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta, datetime
from .processes import user_process, content_filtering_process
from .pwd_utils import validate_password_nist
from .services.db_services.user_service import get_user_by_email, update_user_password
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_GET
from django.core.cache import cache
from forum.services.db_services.user_service import authenticate_user
from forum.ip_utils import get_client_ip

import subprocess
import re
import random
import string

# Constants for validation
FILTER_CONTENT_REGEX = r"^[\w '.@*-]+$"
FILTER_CONTENT_MAX_LENGTH = 255

LOGIN_HTML = "html/login_view.html"
RESET_HTML = "html/reset_password_view.html"
CHAT_LANDING_HTML = "html/chat_landing.html"
SESSION_EXPIRED_MSG = "Session Expired! Please login again."
INVALID_ACCESS_MSG = "Invalid Access!"
LOGIN_PATH = "/login"


def validate_filter_content(content):
    """
    Validate filter content against our rules.
    Returns (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "Content cannot be empty."

    content = content.strip()

    if len(content) > FILTER_CONTENT_MAX_LENGTH:
        return False, f"Content is too long (max {FILTER_CONTENT_MAX_LENGTH} characters)."

    if not re.match(FILTER_CONTENT_REGEX, content):
        return False, "Invalid characters. Allowed: letters, numbers, underscores, spaces, hyphens, apostrophes, periods, '@', '*'."

    return True, ""


# MARK: Index View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def index(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

        username = context["user_info"]["Username"]
        context["partners"] = ChatRoom.get_recent_partners_for_user(username)
    else:
        context["user_info"] = None
        context["partners"] = []

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    total_post_count = 0

    post_count_response = post_service.get_total_post_count()
    if post_count_response["status"] == "SUCCESS":
        # total_post_count: int = post_count_response["data"]["total_post_count"]
        total_post_count = post_count_response["data"]["total_post_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_post_count)

    posts_response = post_service.get_posts_for_page(
        pagination_data["start_index"], per_page)
    if posts_response["status"] == "SUCCESS":
        context["posts"] = posts_response["data"]["posts"]

    context.update(pagination_data)

    return render(request, "html/index.html", context)


# MARK: Login View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request, context=None):

    if context is None:
        context = {}

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        result = authenticate_user(email, password)

        if result and result.get("status") == "SUCCESS":
            return render(request, LOGIN_HTML, context)

        else:
            return render(request, LOGIN_HTML)

    return render(request, LOGIN_HTML)

# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.


@require_http_methods(["GET", "POST"])
@csrf_protect
def logout_view(request, context=None):

    if context is None:
        context = {}

    if request.method == 'POST':
        logout(request)
        session_utils.clear_session(request)

        messages.success(request, "You have been successfully logged out.")
        return redirect('index')

    messages.error(
        request, "Invalid logout request. Please use the logout button.")
    return redirect('user_profile_view')


# MARK: Register View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def register_view(request, context=None):

    if context is None:
        context = {}

    messages = get_messages(request)
    for message in messages:
        context["error"] = message

    return render(request, 'html/register_view.html', {
        'RECAPTCHA_PUBLIC_KEY': settings.RECAPTCHA_PUBLIC_KEY,
        **context,
    })


# MARK: Email Verification View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def email_verification(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        session_code = request.custom_session.get("verification_code")
        attempts = request.custom_session.get("verification_attempts", 0)
        code_generated_at_str = request.custom_session.get("code_generated_at")

        performed_by = 1
        email = request.custom_session.get(
            "pending_user") or request.custom_session.get("reset_email")

        if email:
            response = user_service.get_user_by_email(email)
            if response["status"] == "SUCCESS":
                performed_by = response["data"]["UserID"]

        if not session_code or not code_generated_at_str:
            msg = "Verification session is invalid or expired."
            messages.error(request, msg)
            log_service.log_action(
                msg, performed_by, isSystem=False, isError=True)
            return redirect("login_view")

        try:
            code_generated_at = timezone.datetime.fromisoformat(
                code_generated_at_str)
            if timezone.is_naive(code_generated_at):
                code_generated_at = timezone.make_aware(code_generated_at)

            if timezone.now() > code_generated_at + timedelta(minutes=5):
                msg = "Your verification code has expired. Please request a new one."
                messages.error(request, msg)
                log_service.log_action(
                    msg, performed_by, isSystem=False, isError=True)

                for key in ['verification_code', 'code_generated_at', 'verification_attempts']:
                    if key in request.custom_session:
                        del request.custom_session[key]

                request.custom_session.save()

                if request.custom_session.get('reset_email'):
                    return redirect("forgot_password_view")

                return redirect("login_view")

        except Exception as e:
            msg = f"There was an error validating your session: {e}"
            messages.error(
                request, "There was an error validating your session.")
            log_service.log_action(
                msg, performed_by, isSystem=True, isError=True)
            return redirect("login_view")

        if code != session_code:
            attempts += 1
            request.custom_session["verification_attempts"] = attempts
            request.custom_session.save()

            msg = f"Incorrect code. Attempt {attempts}/3."
            messages.error(request, msg)
            log_service.log_action(
                msg, performed_by, isSystem=False, isError=True)

            if attempts >= 3:
                final_msg = "Too many failed attempts. Please try again later."
                messages.error(request, final_msg)
                log_service.log_action(
                    final_msg, performed_by, isSystem=False, isError=True)
                return redirect("login_view")

            return redirect("email_verification")

        if not email:
            msg = "Verification session is incomplete. Please try again."
            messages.error(request, msg)
            log_service.log_action(
                msg, performed_by, isSystem=True, isError=True)
            return redirect("login_view")

        response = user_service.get_user_by_email(email)
        if response["status"] != "SUCCESS":
            msg = f"Account not found for verification: {email}"
            messages.error(request, "Account not found for this verification.")
            log_service.log_action(
                msg, performed_by, isSystem=True, isError=True)
            return redirect("login_view")

        user_data = response["data"]
        performed_by = user_data["UserID"]

        if request.custom_session.get("pending_user"):
            session_response = session_utils.setup_session(request, user_data)
            if session_response["status"] != "SUCCESS":
                msg = f"Verification succeeded for '{email}', but failed to log in."
                messages.error(
                    request, "Verification succeeded, but failed to log in.")
                log_service.log_action(
                    msg, performed_by, isSystem=True, isError=True)
                return redirect("login_view")

            msg = f"Email verification for '{email}' succeeded, user logged in."
            messages.success(
                request, "Your account has been verified and you're now logged in.")
            log_service.log_action(
                msg, performed_by, isSystem=False, isError=False)
            redirect_target = "index"

        elif request.custom_session.get("reset_email"):
            request.custom_session["verified_for_reset"] = True
            request.custom_session.save()

            msg = f"Verification for '{email}' succeeded, proceeding to password reset."
            messages.success(
                request, "Verification successful. Please reset your password.")
            log_service.log_action(
                msg, performed_by, isSystem=False, isError=False)
            redirect_target = "reset_password_view"

        else:
            msg = "Verification failed: unclear session state."
            messages.error(request, "Session state unclear. Please try again.")
            log_service.log_action(
                msg, performed_by, isSystem=True, isError=True)
            return redirect("login_view")

        if request.custom_session.get("pending_user"):
            for key in ['pending_user', 'verification_code', 'code_generated_at', 'verification_attempts']:
                if key in request.custom_session:
                    del request.custom_session[key]
            request.custom_session.save()

        return redirect(redirect_target)

    return render(request, "html/email_verification.html")


# MARK: Post Form View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def post_form_view(request, context=None, post_id=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    if post_id != None:
        post_response = post_service.get_post_by_id(post_id)
        if post_response["status"] == "SUCCESS":
            context["post"] = post_response["data"]["post"]

    return render(request, "html/post_form_view.html", context)

# Safe: Only POST is used to retrieve filtered words securely; no unsafe operations are performed.


@require_http_methods(["POST"])
def filtered_words_api(request):
    # Delegate to process layer
    response = content_filtering_process.process_get_all_filtered_words_api(
        request)
    return JsonResponse(response)


# MARK: Post View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def post_view(request, post_id, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]

    per_page = 2
    current_page = int(request.GET.get("page", 1))

    total_comment_count = context["post"]["CommentCount"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_comment_count)

    comments_response = comment_service.get_comments_for_page(
        pagination_data["start_index"], per_page, postID=post_id)
    if comments_response["status"] == "SUCCESS":
        context["comments"] = comments_response["data"]["comments"]

    context.update(pagination_data)

    return render(request, "html/post_view.html", context)


# MARK: User Profile View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def user_profile_view(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")
    # else:
    #     return redirect('index')

    user_response = user_service.get_user_by_id(context["user_info"]["UserID"])
    if user_response["status"] == "SUCCESS":
        context["user_data"] = user_response["data"]

    return render(request, "html/user_profile_view.html", context)


# MARK: User Manage Post View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def user_manage_post_view(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")
    # else:
    #     return redirect('index')

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    post_count_response = post_service.get_total_post_count(
        userID=context["user_info"]["UserID"])
    if post_count_response["status"] == "SUCCESS":
        total_post_count: int = post_count_response["data"]["total_post_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_post_count)

    posts_response = post_service.get_posts_for_page(
        pagination_data["start_index"], per_page, userID=context["user_info"]["UserID"])
    if posts_response["status"] == "SUCCESS":
        context["posts"] = posts_response["data"]["posts"]

    context.update(pagination_data)

    return render(request, "html/user_manage_post_view.html", context)


# MARK: Admin Manage Post View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def admin_manage_post_view(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    if context["user_info"]["Role"] != "admin":
        messages.error(request, INVALID_ACCESS_MSG)
        return redirect("login_view")

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    total_post_count = 0

    post_count_response = post_service.get_total_post_count()
    if post_count_response["status"] == "SUCCESS":
        # total_post_count: int = post_count_response["data"]["total_post_count"]
        total_post_count = post_count_response["data"]["total_post_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_post_count)

    posts_response = post_service.get_posts_for_page(
        pagination_data["start_index"], per_page)
    if posts_response["status"] == "SUCCESS":
        context["posts"] = posts_response["data"]["posts"]

    context.update(pagination_data)

    return render(request, "html/admin_manage_post_view.html", context)

# MARK: User Manage Comment View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.


@require_http_methods(["GET", "POST"])
@csrf_protect
def user_manage_comment_view(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")
    # else:
    #     return redirect('index')

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    comment_count_response = comment_service.get_total_comment_count(
        context["user_info"]["UserID"])
    if comment_count_response["status"] == "SUCCESS":
        total_comment_count: int = comment_count_response["data"]["total_comment_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_comment_count)

    comments_response = comment_service.get_comments_for_page(
        pagination_data["start_index"], per_page, userID=context["user_info"]["UserID"])
    if comments_response["status"] == "SUCCESS":
        context["comments"] = comments_response["data"]["comments"]

    context.update(pagination_data)

    return render(request, "html/user_manage_comment_view.html", context)


# MARK: Admin Manage Comment View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def admin_manage_comment_view(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    if context["user_info"]["Role"] != "admin":
        messages.error(request, INVALID_ACCESS_MSG)
        return redirect("login_view")

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    comment_count_response = comment_service.get_total_comment_count()
    if comment_count_response["status"] == "SUCCESS":
        total_comment_count: int = comment_count_response["data"]["total_comment_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_comment_count)

    comments_response = comment_service.get_comments_for_page(
        pagination_data["start_index"], per_page)
    if comments_response["status"] == "SUCCESS":
        context["comments"] = comments_response["data"]["comments"]

    context.update(pagination_data)

    return render(request, "html/admin_manage_comment_view.html", context)

# MARK: Admin View log
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.


@require_http_methods(["GET", "POST"])
@csrf_protect
def admin_logs_view(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    if context["user_info"]["Role"] != "admin":
        messages.error(request, INVALID_ACCESS_MSG)
        return redirect("login_view")

    search = request.GET.get("search", "")
    context["search"] = search
    category = request.GET.get("category", "")
    context["category"] = category
    sort_by = request.GET.get("sort_by", "newest")
    context["sort_by"] = sort_by

    per_page = 25
    current_page = int(request.GET.get("page", 1))

    log_count_response = log_service.get_total_log_count(search, category)
    if log_count_response["status"] == "SUCCESS":
        total_log_count: int = log_count_response["data"]["total_log_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_log_count)

    logs_response = log_service.get_logs_for_page(
        pagination_data["start_index"], per_page, sort_by, search, category)
    if logs_response["status"] == "SUCCESS":
        context["logs"] = logs_response["data"]["logs"]

    context.update(pagination_data)

    return render(request, "html/admin_logs_view.html", context)

# MARK: Forgot Password View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.


@require_http_methods(["GET", "POST"])
@csrf_protect
def forgot_password_view(request):
    context = {}

    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        user_check = user_service.get_user_by_email(email)
        if user_check["status"] != "SUCCESS":
            context["error"] = "No account found with that email."
            return render(request, "html/forgot_password_view.html", context)

        otp = user_process.generate_verification_code()
        request.session["reset_email"] = email
        request.session["verification_code"] = otp  # Correct key
        request.session["code_generated_at"] = timezone.now(
        ).isoformat()  # Correct key

        send_mail(
            subject="Your Password Reset Code",
            message=f"Your password reset code is: {otp}",
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
        )

        context["message"] = "A reset code has been sent to your email."
        return redirect("email_verification")

    return render(request, "html/forgot_password_view.html", context)


# MARK: Reset Password View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def reset_password_view(request):

    user_email = request.session.get("reset_email")

    if request.method == "POST":
        try:
            new_password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")

            if new_password != confirm_password:
                return render(request, RESET_HTML, {"error": "Passwords do not match."})

            status, msg = validate_password_nist(new_password)
            if not status:
                return render(request, RESET_HTML, {"error": msg})

            # Fetch user by email
            response = get_user_by_email(user_email)
            if response["status"] != "SUCCESS":
                return render(request, RESET_HTML, {"error": "User not found."})

            user_id = response["data"]["UserID"]
            update_response = update_user_password(user_id, new_password)
            if update_response["status"] != "SUCCESS":
                return render(request, RESET_HTML, {"error": "Password reset failed."})

            # Clean up session
            for key in ['reset_email', 'verification_code', 'code_generated_at', 'verified_for_reset']:
                request.session.pop(key, None)

            messages.success(
                request, "Password has been reset successfully. You may now log in.")
            return redirect("login_view")

        except Exception as e:
            print("Password reset error:", e)
            return HttpResponse("Server error during password reset", status=500)

    return render(request, RESET_HTML)


# MARK: Chat View
# Safe: Chat view only renders based on GET; CSRF and iframe controls are in place.
@require_GET
@csrf_protect
@xframe_options_exempt
def chat_view(request, other_user):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        if request.GET.get("frame") == "1":
            return render(request, "html/chat_not_logged_in.html", status=401)
        return redirect(f"/login/?next=/chat/{other_user}/")

    user_info = session_response["data"]

    if not UserAccount.objects.filter(Username__iexact=other_user).exists():
        return render(request, CHAT_LANDING_HTML, {
            "user_info": user_info,
            "error":     "User does not exist."
        })

    username = user_info.get("Username", "").strip()

    if request.GET.get("frame") != "1":
        # Always redirect full view to iframe
        return redirect(f"/chat/{other_user}/?frame=1")

    # Load unread count if available
    a, b = sorted([username.lower(), other_user.lower()])
    room_name = f"private_{a}_{b}"

    return render(request, "html/chat_inner.html", {
        "user_info": user_info,
        "other_user": other_user,
        # "unread_count": unread_count,
    })

# Safe: Only GET used to load chat landing or redirect based on session.


@require_GET
@csrf_protect
@xframe_options_exempt
def chat_landing_or_redirect_view(request):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect(LOGIN_PATH)

    user_info = session_response["data"]
    username = user_info["Username"]

    # Query for chat partners
    partners = ChatRoom.get_recent_partners_for_user(username)

    if partners:
        if request.GET.get("frame") == "1":
            return redirect(f"/chat/{partners[0]}/?frame=1")
        return redirect(f"/chat/{partners[0]}")

    return render(request, CHAT_LANDING_HTML, {"user_info": user_info})

# Safe: Only GET used to load chat landing or redirect based on session.


@require_GET
@csrf_protect
@xframe_options_exempt
def chat_home_view(request):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect(LOGIN_PATH)

    user_info = session_response["data"]
    username = user_info["Username"]

    partners = ChatRoom.get_recent_partners_for_user(username)

    if partners:
        return redirect('chat_view', other_user=partners[0])

    return render(request, 'chat_landing.html', {'error': 'No chats yet.'})

# Safe: Only GET used to load chat landing or redirect based on session.


@require_GET
@csrf_protect
@xframe_options_exempt
def start_chat_view(request):
    session = session_utils.check_session(request)
    if session["status"] != "SUCCESS":
        return redirect(LOGIN_PATH)

    user_info = session["data"]
    username = request.GET.get("username", "").strip().lower()

    if not username or username == user_info["Username"].lower():
        return render(request, CHAT_LANDING_HTML, {
            "user_info": user_info,
            "error": "Invalid",
        })

    if not UserAccount.objects.filter(Username__iexact=username).exists():
        return render(request, CHAT_LANDING_HTML, {
            "user_info": user_info,
            "error": "User does not exist.",
        })

    return redirect(f"/chat/{username}/")


# MARK: Filtered Words View
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def manage_filtered_words_view(request):
    # session and authorization
    session_resp = session_utils.check_session(request)
    if session_resp.get('status') != 'SUCCESS':
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('login_view')
    user = session_resp.get('data', {})
    if user.get('Role') != 'admin':
        messages.error(request, 'Administrator access required.')
        return redirect('index')

    # build context
    context = {
        'user_info': user,
        'search_term': request.GET.get('search', '').strip(),
        'sort_by': request.GET.get('sort_by', 'FilterContent'),
        'sort_order': request.GET.get('sort_order', 'ASC'),
        'current_page': int(request.GET.get('page', 1)),
    }

    # handle POST actions
    if request.method == 'POST':
        if request.POST.get('bulk_action') == 'delete_selected':
            return content_filtering_process.process_bulk_delete_filtered_words(request, context)
        if 'delete_id' in request.POST:
            return content_filtering_process.process_delete_filtered_word(request, context)
        if 'edit_filter_content' in request.POST and 'edit_id' in request.POST:
            return content_filtering_process.process_update_filtered_word(request, context)
        if 'filter_content' in request.POST:
            return content_filtering_process.process_add_filtered_words(request, context)

    # prefill edit form if needed
    edit = request.GET.get('edit')
    if edit:
        context.update(content_filtering_process.process_get_edit_word(edit))

    # get list for display
    context.update(
        content_filtering_process.process_get_filtered_words_for_display(context))
    return render(request, 'html/filtered_words_manage.html', context)

# MARK: Admin User Portal
# Safe: Only GET is used to load admin portal view with no unsafe actions.


@require_GET
def admin_portal(request):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect(LOGIN_PATH)

    user_info = session_response["data"]
    if user_info["Role"].lower() != "admin":
        return redirect("/")

    users = UserAccount.objects.all()
    return render(request, "html/admin_portal.html", {"users": users, "user_info": user_info})

# MARK: Change User Role Process


@require_POST
def change_user_role(request, user_id):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect(LOGIN_PATH)

    user_info = session_response["data"]
    if user_info["Role"].lower() != "admin":
        return redirect("/")

    return user_process.process_update_user_role(request, user_id)


@require_POST
def delete_user(request, user_id):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect(LOGIN_PATH)

    user_info = session_response["data"]
    if user_info["Role"].lower() != "admin":
        return redirect("/")

    return user_process.process_delete_user(request, user_id)

# MARK: Search Posts View
# Safe: Only GET is used to query and display posts; no mutations are done.


@require_GET
def search_posts_view(request):
    context = {}
    session_response = session_utils.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    # Get search query and sort parameters
    search_query = request.GET.get("q", "")
    sort_order = request.GET.get("sort", "newest")  # Default to newest first

    # Configure pagination
    per_page = 10
    current_page = int(request.GET.get("page", 1))

    # Get total count for pagination
    count_response = post_service.get_search_post_count(
        keyword=search_query
    )
    total_count = count_response["data"]["count"] if count_response["status"] == "SUCCESS" else 0

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_count
    )

    # Call service with search + sorting
    response = post_service.search_posts_by_keyword(
        keyword=search_query,
        start_index=pagination_data["start_index"],
        per_page=per_page,
        sort_order=sort_order
    )

    context.update({
        "posts": response["data"]["posts"] if response["status"] == "SUCCESS" else [],
        "search_query": search_query,
        "request": request,
        "page_range": pagination_data["page_range"],
        "current_page": current_page,
        "total_pages": pagination_data["total_pages"],
        "previous_page": pagination_data["previous_page"],
        "next_page": pagination_data["next_page"]
    })

    return render(request, "html/index.html", context)

# MARK: Banned View
# Safe: Only GET is allowed for rendering banned notice.


@require_GET
def banned_view(request):
    return render(request, "html/banned.html", status=403)
