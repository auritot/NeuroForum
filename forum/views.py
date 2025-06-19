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
from .services import session_service, utilities
from .services.db_services import user_service, post_service, comment_service, ContentFiltering_service
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta, datetime
from .processes import user_process
from .pwd_utils import validate_password_nist

import re
import random
import string

# Constants for validation
FILTER_CONTENT_REGEX = r"^[\w '.@*-]+$"
FILTER_CONTENT_MAX_LENGTH = 255


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

def index(request, context={}):
    session_response = session_service.check_session(request)
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

def login_view(request, context={}):
    messages = get_messages(request)
    for message in messages:
        context["error"] = message

    return render(request, "html/login_view.html", context)


def logout_view(request, context={}):
    if request.method == 'POST':
        logout(request)
        session_service.clear_session(request)

        messages.success(request, "You have been successfully logged out.")
        return redirect('index')

    messages.error(
        request, "Invalid logout request. Please use the logout button.")
    return redirect('user_profile_view')


# MARK: Register View

def register_view(request, context={}):
    messages = get_messages(request)
    for message in messages:
        context["error"] = message

    # return render(request, "html/register_view.html", context)
    return render(request, 'html/register_view.html', {
        'RECAPTCHA_PUBLIC_KEY': settings.RECAPTCHA_PUBLIC_KEY,
        **context,
    })


# MARK: Email Verification View

def email_verification(request):
    error = None
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        session_code = request.session.get("verification_code")
        attempts = request.session.get("verification_attempts", 0)
        code_generated_at = request.session.get("code_generated_at")

        # check expiry
        if not code_generated_at or timezone.now() > datetime.fromisoformat(code_generated_at) + timedelta(minutes=5):
            messages.error(request, "Verification code expired.")
            return redirect("login_view")

        if code != session_code:
            attempts += 1
            request.session['verification_attempts'] = attempts
            if attempts >= 3:
                # Lock out the account (you can add user_service.lock_account(email) here)
                messages.error(
                    request, "Too many failed attempts. Account temporarily locked.")
                return redirect("login_view")
            messages.error(request, f"Incorrect code. Attempt {attempts}/3.")
            return redirect("email_verification")

        # Determine purpose
        email = request.session.get("pending_user") or request.session.get("reset_email")
        response = user_service.get_user_by_email(email)

        if response["status"] != "SUCCESS":
            messages.error(request, "User not found.")
            return redirect("login_view")

        user_data = response["data"]

        # Setup session only if it's a registration
        if "pending_user" in request.session:
            # Registration: Log in the user
            session_response = session_service.setup_session(request, user_data)
            if session_response["status"] != "SUCCESS":
                messages.error(request, "Failed to log in after verification.")
                return redirect("login_view")
            redirect_target = "index"
        else:
            # Password reset: move to reset password form
            redirect_target = "process_change_password"

        # Clean up session keys
        for key in ['pending_user', 'reset_email', 'verification_code', 'code_generated_at', 'verification_attempts']:
            request.session.pop(key, None)

        return redirect(redirect_target)

    return render(request, "html/email_verification.html")


# MARK: Post Form View

def post_form_view(request, context={}, post_id=None):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    if post_id != None:
        post_response = post_service.get_post_by_id(post_id)
        if post_response["status"] == "SUCCESS":
            context["post"] = post_response["data"]["post"]

    return render(request, "html/post_form_view.html", context)


def filtered_words_api(request):
    response = ContentFiltering_service.get_all_filtered_words()
    # Return full response (status, message, data) as JSON
    return JsonResponse(response)


# MARK: Post View

def post_view(request, post_id, context={}):
    session_response = session_service.check_session(request)
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

def user_profile_view(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")
    # else:
    #     return redirect('index')

    user_response = user_service.get_user_by_id(context["user_info"]["UserID"])
    if user_response["status"] == "SUCCESS":
        context["user_data"] = user_response["data"]

    return render(request, "html/user_profile_view.html", context)


# MARK: User Manage Post View

def user_manage_post_view(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
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


# MARK: User Manage Comment View

def user_manage_comment_view(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")
    # else:
    #     return redirect('index')

    per_page = 2
    current_page = int(request.GET.get("page", 1))

    comment_count_response = comment_service.get_total_comment_count_by_user_id(
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


# MARK: Forgot Password View

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
        request.session["reset_otp"] = otp
        request.session["otp_created_at"] = timezone.now().isoformat()

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
def reset_password_view(request):
    user_email = request.session.get("reset_email")
    if not user_email:
        messages.error(request, "Session expired. Please restart the reset process.")
        return redirect("forgot_password_view")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            return render(request, "reset_password_view.html", {"error": "Passwords do not match."})

        password_check = validate_password_nist(new_password)
        if password_check["status"] != "PASS":
            return render(request, "reset_password_view.html", {"error": password_check["message"]})

        try:
            user = UserAccount.objects.get(Email=user_email)
            user.Password = new_password  # hash if needed
            user.save()
            for key in ['pending_user', 'verification_code', 'code_generated_at']:
                request.session.pop(key, None)
            messages.success(request, "Password has been reset successfully. You may now log in.")
            return redirect("login_view")
        except UserAccount.DoesNotExist:
            return render(request, "reset_password_view.html", {"error": "User not found."})

    for key in ['reset_email', 'verification_code', 'code_generated_at']:
        request.session.pop(key, None)

    return render(request, "reset_password_view.html")

# MARK: Chat View

@xframe_options_exempt
def chat_view(request, other_user):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        if request.GET.get("frame") == "1":
            return render(request, "html/chat_not_logged_in.html", status=401)
        return redirect(f"/login/?next=/chat/{other_user}/")

    user_info = session_response["data"]

    if not UserAccount.objects.filter(Username__iexact=other_user).exists():
        return render(request, "html/chat_landing.html", {
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


@xframe_options_exempt
def chat_landing_or_redirect_view(request):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect("/login")

    user_info = session_response["data"]
    username = user_info["Username"]

    # Query for chat partners
    partners = ChatRoom.get_recent_partners_for_user(username)

    if partners:
        if request.GET.get("frame") == "1":
            return redirect(f"/chat/{partners[0]}/?frame=1")
        return redirect(f"/chat/{partners[0]}")

    return render(request, "html/chat_landing.html", {"user_info": user_info})


@xframe_options_exempt
def chat_home_view(request):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect("/login")

    user_info = session_response["data"]
    username = user_info["Username"]

    partners = ChatRoom.get_recent_partners_for_user(username)

    if partners:
        return redirect('chat_view', other_user=partners[0])

    return render(request, 'chat_landing.html', {'error': 'No chats yet.'})


@xframe_options_exempt
def start_chat_view(request):
    session = session_service.check_session(request)
    if session["status"] != "SUCCESS":
        return redirect("/login")

    user_info = session["data"]
    username = request.GET.get("username", "").strip().lower()

    if not username or username == user_info["Username"].lower():
        return render(request, "html/chat_landing.html", {
            "user_info": user_info,
            "error": "Invalid",
        })

    if not UserAccount.objects.filter(Username__iexact=username).exists():
        return render(request, "html/chat_landing.html", {
            "user_info": user_info,
            "error": "User does not exist.",
        })

    return redirect(f"/chat/{username}/")


# MARK: Filtered Words View

def manage_filtered_words_view(request):
    from .services.db_services import ContentFiltering_service
    session_resp = session_service.check_session(request)

    if session_resp.get("status") != "SUCCESS":
        messages.error(request, "You must be logged in to access this page.")
        return redirect('login_view')

    user_data = session_resp.get("data", {})
    actual_role_in_session = user_data.get("Role")

    # Check if the user's Role is 'admin'
    if actual_role_in_session != "admin":
        # UPDATED MESSAGE
        messages.error(
            request, "You do not have permission to access this page. Administrator access required.")
        return redirect('index')

    context = {}
    # Add user_info to the context if the session is valid and user is authorized
    # This ensures the base template can correctly render the toolbar
    if session_resp.get("status") == "SUCCESS":
        # user_data comes from session_resp.get("data", {})
        context["user_info"] = user_data

    per_page = 10
    current_page = int(request.GET.get("page", 1))
    search_term = request.GET.get("search", "").strip()
    sort_by = request.GET.get("sort_by", "FilterContent")
    sort_order = request.GET.get("sort_order", "ASC")

    context['search_term'] = search_term
    context['sort_by'] = sort_by
    context['sort_order'] = sort_order
    context['current_page'] = current_page

    edit_id = request.GET.get("edit")
    if edit_id and edit_id.isdigit():
        edit_response = ContentFiltering_service.get_filtered_word_by_id(
            edit_id)
        if edit_response["status"] == "SUCCESS":
            context["edit_word"] = edit_response["data"]
        else:
            messages.error(
                request, f"Could not find word with ID {edit_id} to edit.")
            # Build query params for redirect without edit_id
            base_redirect_url_no_edit = reverse('manage_wordfilter')
            query_params_no_edit = {k: v for k, v in context.items(
            ) if k in ['page', 'search', 'sort_by', 'sort_order'] and v}
            redirect_url_no_edit = f"{base_redirect_url_no_edit}?{urlencode(query_params_no_edit)}" if query_params_no_edit else base_redirect_url_no_edit
            return redirect(redirect_url_no_edit)

    base_redirect_url = reverse('manage_wordfilter')
    query_params_for_redirect = {
        'page': current_page,
        'search': search_term,
        'sort_by': sort_by,
        'sort_order': sort_order
    }
    cleaned_query_params = {k: v for k, v in query_params_for_redirect.items(
    ) if v is not None and str(v).strip() != ''}
    redirect_url_with_params = f"{base_redirect_url}?{urlencode(cleaned_query_params)}" if cleaned_query_params else base_redirect_url

    if request.method == "POST":
        # Flag to indicate if a POST action was processed        # --- Action: Bulk Delete ---
        action_taken = False
        if request.POST.get("bulk_action") == "delete_selected":
            selected_ids = request.POST.getlist("selected_words")
            filter_ids_to_delete = [
                fid for fid in selected_ids if fid and fid.isdigit()]

            # Get pagination params from POST (hidden form fields)
            page_from_form = request.POST.get("page", current_page)
            search_from_form = request.POST.get("search", search_term)
            sort_by_from_form = request.POST.get("sort_by", sort_by)
            sort_order_from_form = request.POST.get("sort_order", sort_order)

            if not filter_ids_to_delete:
                messages.warning(request, "No words selected for deletion.")
            else:
                resp = ContentFiltering_service.delete_filtered_words_by_ids(
                    filter_ids_to_delete)
                if resp.get("status") == "SUCCESS":
                    # Service message includes count
                    messages.success(request, resp.get("message"))
                elif resp.get("status") == "NOT_FOUND":
                    messages.warning(request, resp.get("message"))
                else:  # ERROR
                    messages.error(request, resp.get(
                        "message", "An error occurred during bulk deletion."))

            # Redirect back to list with form parameters
            base_url = reverse('manage_wordfilter')
            delete_params = {
                'page': page_from_form,
                'search': search_from_form,
                'sort_by': sort_by_from_form,
                'sort_order': sort_order_from_form
            }
            cleaned_params = {k: v for k, v in delete_params.items(
            ) if v is not None and str(v).strip() != ''}
            return redirect(f"{base_url}?{urlencode(cleaned_params)}")

        # --- Action: Single Delete ---
        # This will only be checked if not a bulk_action.
        elif "delete_id" in request.POST:
            filter_id = request.POST.get("delete_id")

            # Get pagination params from POST (hidden form fields)
            page_from_form = request.POST.get("page", current_page)
            search_from_form = request.POST.get("search", search_term)
            sort_by_from_form = request.POST.get("sort_by", sort_by)
            sort_order_from_form = request.POST.get("sort_order", sort_order)

            if filter_id and filter_id.isdigit():
                resp = ContentFiltering_service.delete_filtered_word_by_id(
                    filter_id)
                if resp.get("status") == "SUCCESS":
                    messages.success(
                        request, f"Successfully deleted word ID {filter_id} from the filter list.")
                else:
                    messages.error(request, resp.get(
                        "message", f"An error occurred while deleting word ID {filter_id}."))
            else:
                messages.error(
                    request, "Invalid or missing ID for single deletion.")

            # Redirect back to list with form parameters
            base_url = reverse('manage_wordfilter')
            delete_params = {
                'page': page_from_form,
                'search': search_from_form,
                'sort_by': sort_by_from_form,
                'sort_order': sort_order_from_form
            }
            cleaned_params = {k: v for k, v in delete_params.items(
            ) if v is not None and str(v).strip() != ''}
            # --- Action: Add Word(s) ---
            return redirect(f"{base_url}?{urlencode(cleaned_params)}")
        # Ensure it's not an edit form submission and not a delete action (already handled above).
        elif "filter_content" in request.POST and not request.GET.get("edit"):
            content_input = request.POST.get("filter_content", "").strip()

            # Get pagination params from POST (hidden form fields)
            page_from_form = request.POST.get("page", current_page)
            search_from_form = request.POST.get("search", search_term)
            sort_by_from_form = request.POST.get("sort_by", sort_by)
            sort_order_from_form = request.POST.get("sort_order", sort_order)

            # Split by newline, strip each line, and filter out empty lines
            words_to_add = [word.strip()
                            for word in content_input.splitlines() if word.strip()]

            if not words_to_add:
                messages.error(
                    request, "No words provided to add. Please enter words in the textarea, one per line.")
            else:
                valid_words = []
                invalid_word_entries = []  # Store original invalid entries for feedback
                all_entries_valid = True

                for original_word_entry in words_to_add:
                    # Validate each word individually using centralized validation
                    is_valid, error_msg = validate_filter_content(
                        original_word_entry)
                    if is_valid:
                        # Keep original case for potential display, service will lowercase
                        valid_words.append(original_word_entry)
                    else:
                        all_entries_valid = False
                        if len(invalid_word_entries) < 5:  # Show a few examples
                            invalid_word_entries.append(original_word_entry)

                if not all_entries_valid:
                    error_msg = f"One or more words are invalid. Allowed: letters, numbers, underscores, spaces, hyphens, apostrophes, periods, '@', '*'. Max {FILTER_CONTENT_MAX_LENGTH} characters per word."
                    if invalid_word_entries:
                        error_msg += f" Examples of invalid entries: '{', '.join(invalid_word_entries[:3])}'."
                    messages.error(request, error_msg)
                else:  # All words intended for addition are valid
                    if len(valid_words) == 1:
                        resp = ContentFiltering_service.insert_filtered_word(
                            valid_words[0])
                        if resp.get("status") == "SUCCESS":
                            messages.success(
                                request, f'Successfully added "{valid_words[0]}" to the filter list.')
                        else:
                            messages.error(request, resp.get(
                                "message", "An error occurred while adding the word."))
                    elif len(valid_words) > 1:
                        resp = ContentFiltering_service.insert_multiple_filtered_words(
                            valid_words)
                        # The service's response message for insert_multiple_filtered_words is already detailed
                        if resp.get("status") == "SUCCESS" or resp.get("status") == "INFO":
                            added_count = resp.get(
                                "data", {}).get("added_count", 0)
                            if added_count > 0:
                                messages.success(request, resp.get("message"))
                            else:  # Only skipped or no valid words processed by service
                                messages.warning(request, resp.get("message"))
                        else:  # ERROR case from service
                            messages.error(request, resp.get(
                                "message", "An error occurred during bulk add."))

            # Redirect back to list with form parameters
            base_url = reverse('manage_wordfilter')
            add_params = {
                'page': page_from_form,
                'search': search_from_form,
                'sort_by': sort_by_from_form,
                'sort_order': sort_order_from_form
            }
            cleaned_params = {k: v for k, v in add_params.items(
            ) if v is not None and str(v).strip() != ''}
            return redirect(f"{base_url}?{urlencode(cleaned_params)}")
            # --- Action: Update Word ---
        # Ensure it's an edit form submission (check POST params for edit_id and edit_filter_content)
        elif "edit_filter_content" in request.POST and "edit_id" in request.POST:
            edit_id_from_form = request.POST.get("edit_id")
            content = request.POST.get("edit_filter_content", "").strip()

            # Get pagination params from POST (hidden form fields)
            page_from_form = request.POST.get("page", current_page)
            search_from_form = request.POST.get("search", search_term)
            sort_by_from_form = request.POST.get("sort_by", sort_by)
            sort_order_from_form = request.POST.get("sort_order", sort_order)

            if not edit_id_from_form or not edit_id_from_form.isdigit():
                messages.error(request, "Invalid ID for editing.")
                # Stay in edit mode for error
                base_url = reverse('manage_wordfilter')
                error_params = {
                    'edit': edit_id_from_form,
                    'page': page_from_form,
                    'search': search_from_form,
                    'sort_by': sort_by_from_form,
                    'sort_order': sort_order_from_form
                }
                cleaned_params = {k: v for k, v in error_params.items(
                ) if v is not None and str(v).strip() != ''}
                return redirect(f"{base_url}?{urlencode(cleaned_params)}")
            else:
                is_valid, error_msg = validate_filter_content(content)
                if is_valid:
                    resp = ContentFiltering_service.update_filtered_word_by_id(
                        edit_id_from_form, content)
                    if resp.get("status") == "SUCCESS":
                        messages.success(
                            request, f'Successfully updated word ID {edit_id_from_form} to "{content}".')
                        # Success: redirect to list without edit parameter
                        base_url = reverse('manage_wordfilter')
                        success_params = {
                            'page': page_from_form,
                            'search': search_from_form,
                            'sort_by': sort_by_from_form,
                            'sort_order': sort_order_from_form
                        }
                        cleaned_params = {k: v for k, v in success_params.items(
                        ) if v is not None and str(v).strip() != ''}
                        return redirect(f"{base_url}?{urlencode(cleaned_params)}")
                    else:
                        messages.error(request, resp.get(
                            "message", "An error occurred while updating the word."))
                        # Service error: stay in edit mode
                        base_url = reverse('manage_wordfilter')
                        error_params = {
                            'edit': edit_id_from_form,
                            'page': page_from_form,
                            'search': search_from_form,
                            'sort_by': sort_by_from_form,
                            'sort_order': sort_order_from_form
                        }
                        cleaned_params = {k: v for k, v in error_params.items(
                        ) if v is not None and str(v).strip() != ''}
                        return redirect(f"{base_url}?{urlencode(cleaned_params)}")
                else:
                    messages.error(
                        request, f"Invalid word for update. {error_msg}")
                    # Validation error: stay in edit mode
                    base_url = reverse('manage_wordfilter')
                    error_params = {
                        'edit': edit_id_from_form,
                        'page': page_from_form,
                        'search': search_from_form,
                        'sort_by': sort_by_from_form,
                        'sort_order': sort_order_from_form
                    }
                    cleaned_params = {k: v for k, v in error_params.items(
                    ) if v is not None and str(v).strip() != ''}
                    return redirect(f"{base_url}?{urlencode(cleaned_params)}")
            action_taken = True

        if action_taken:
            return redirect(redirect_url_with_params)
        # else:
            # If a POST request was made but didn't match any known action,
            # it might be an empty form submission or something unexpected.
            # Redirecting is generally safe to prevent resubmission issues.
            # messages.info(request, "No action performed.") # Optional: for debugging
            # return redirect(redirect_url_with_params)

    # GET request or after POST redirect: Fetch data for display
    count_response = ContentFiltering_service.get_total_filtered_words_count(
        search_term=search_term)
    total_filtered_words = 0
    if count_response["status"] == "SUCCESS":
        total_filtered_words = count_response["data"]["total_filtered_words_count"]

    pagination_data = utilities.get_pagination_data(
        current_page, per_page, total_filtered_words)
    context.update(pagination_data)

    response = ContentFiltering_service.get_filtered_words_paginated(
        start_index=pagination_data["start_index"],
        per_page=per_page,
        search_term=search_term,
        sort_by=sort_by,        sort_order=sort_order
    )
    context["filtered_words"] = response["data"] if response["status"] == "SUCCESS" else []

    # Add validation constants to context for template
    context['FILTER_CONTENT_REGEX'] = FILTER_CONTENT_REGEX.replace(
        '^', '').replace('$', '')  # Remove anchors for HTML pattern
    context['FILTER_CONTENT_MAX_LENGTH'] = FILTER_CONTENT_MAX_LENGTH

    return render(request, "html/filtered_words_manage.html", context)


def admin_portal(request):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect("/login")

    user_info = session_response["data"]
    if user_info["Role"].lower() != "admin":
        return redirect("/")

    users = UserAccount.objects.all()
    return render(request, "html/admin_portal.html", {"users": users, "user_info": user_info})


@require_POST
def change_user_role(request, user_id):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect("/login")

    user_info = session_response["data"]
    if user_info["Role"].lower() != "admin":
        return redirect("/")

    role = request.POST.get("role")
    user = get_object_or_404(UserAccount, UserID=user_id)
    user.Role = role
    user.save()
    messages.success(request, f"Updated role for {user.Username} to {role}.")
    return redirect("admin_portal")


@require_POST
def delete_user(request, user_id):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        return redirect("/login")

    user_info = session_response["data"]
    if user_info["Role"].lower() != "admin":
        return redirect("/")

    user = get_object_or_404(UserAccount, UserID=user_id)
    if user.Username.lower() == user_info["Username"].lower():
        messages.error(request, "You cannot delete yourself.")
        return redirect("admin_portal")

    user.delete()
    messages.success(request, f"Deleted user {user.Username}.")
    return redirect("admin_portal")
