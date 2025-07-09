import requests
from ..services import session_utils, utilities
from ..services.db_services import user_service, log_service
from forum.pwd_utils import validate_password_nist
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
import string
import secrets
from django.core.mail import send_mail
from django.utils import timezone
from forum.ip_utils import get_client_ip
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

ERR_MSG = "A problem has occurred. Please try again."
SESSION_EXPIRED_MSG = "Session Expired! Please login again."
USER_NOT_FOUND_MSG = "User not found"

def generate_verification_code(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

# MARK: Process Login
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def process_login(request):
    if request.method != 'POST':
        return redirect('login_view')
    
    ip_address = get_client_ip(request)
    ban_key = f"login_ban_{ip_address}"
    attempts_key = f"login_attempts_{ip_address}"

    print(f"👀 IP login attempt from {ip_address}")
    print(f"🚫 Ban status: {cache.get(ban_key)}")

    if cache.get(ban_key):
        return redirect("banned_view")

    email = utilities.sanitize_input(request.POST.get("email"))
    password = request.POST.get("password", "")

    if not utilities.validate_email(email):
        messages.error(request, "Enter a valid email.")
        log_service.log_action(
            f"Login failed for email '{email}': invalid email format.", 1, isSystem=False, isError=True)
        return redirect("login_view")

    result = user_service.authenticate_user(email, password)

    if result["status"] == "SUCCESS":

        cache.delete(attempts_key)
        cache.delete(ban_key)

        verification_code = generate_verification_code()
        request.session['pending_user'] = email
        request.session['verification_code'] = verification_code
        request.session['code_generated_at'] = timezone.now().isoformat()
        request.session['verification_attempts'] = 0

        subject = "Your verification code"
        message = f"Your verification code is: {verification_code}"

        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
        except Exception as e:
            messages.error(request, f"Failed to send verification email: {e}")
            log_service.log_action(
                f"Login for '{email}': failed to send verification email - {e}", 1, isSystem=True, isError=True)
            return redirect("login_view")

        return redirect("email_verification")
    
    attempts = cache.get(attempts_key, 0) + 1
    cache.set(attempts_key, attempts, timeout=600)
    print(f"❌ Login failed — attempts for {ip_address}: {attempts}")
    logger.warning(f"Login failed for IP {ip_address}")

    if attempts >= 5:
        print(f"🚫 Setting ban for IP: {ip_address}, attempts={attempts}")
        cache.set(ban_key, True, timeout=3600)
        return redirect("banned_view")

    if result["status"] in ["NOT_FOUND", "INVALID"]:
        messages.error(request, "Invalid email or password.")
        log_service.log_action(
            f"Login failed for email '{email}': invalid email or password.", 1, isSystem=False, isError=True)
        return redirect("login_view")

    messages.error(request, ERR_MSG)
    log_service.log_action(
        f"Login failed for email '{email}': unknown error occurred.", 1, isSystem=True, isError=True)
    return redirect("login_view")


# MARK: Process Register
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def process_register(request):
    if request.method != 'POST':
        return redirect('register_view')

    username = utilities.sanitize_input(request.POST.get("username"))
    email = utilities.sanitize_input(request.POST.get("email"))
    password = utilities.sanitize_input(request.POST.get("password"))
    confirmPassword = utilities.sanitize_input(
        request.POST.get("confirmPassword"))

    recaptcha_response = request.POST.get('g-recaptcha-response')
    recaptcha_error_message = None

    if not recaptcha_response:
        recaptcha_error_message = "Please complete the CAPTCHA."
    else:
        VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
        private_key = settings.RECAPTCHA_PRIVATE_KEY

        try:
            response = requests.post(VERIFY_URL, data={
                'secret': private_key,
                'response': recaptcha_response,
                'remoteip': request.META.get('REMOTE_ADDR')
            }, timeout=5)
            result = response.json()
            if not result.get('success'):
                recaptcha_error_message = "CAPTCHA verification failed. Please try again."
                print(
                    f"reCAPTCHA error codes from Google: {result.get('error-codes')}")
        except requests.exceptions.RequestException as e:
            recaptcha_error_message = "Could not verify CAPTCHA due to a network error. Please try again."
            print(f"reCAPTCHA API request failed: {e}")

    if recaptcha_error_message:
        messages.error(request, recaptcha_error_message)
        log_service.log_action(
            f"Registration failed for email '{email}': {recaptcha_error_message}", 1, isSystem=False, isError=True)
        return redirect("register_view")

    if confirmPassword != password:
        messages.error(request, "Passwords does not match.")
        log_service.log_action(
            f"Registration failed for email '{email}': passwords do not match.", 1, isSystem=False, isError=True)
        return redirect("register_view")

    is_valid, error = validate_password_nist(password)
    if not is_valid:
        messages.error(request, error)
        log_service.log_action(
            f"Registration failed for email '{email}': password policy violation - {error}", 1, isSystem=False, isError=True)
        return redirect("register_view")

    if not utilities.validate_email(email):
        messages.error(request, "Enter a valid email.")
        log_service.log_action(
            f"Registration failed for email '{email}': invalid email format.", 1, isSystem=False, isError=True)
        return redirect("register_view")

    username_response = user_service.get_user_by_username(username)
    if username_response["status"] == "SUCCESS":
        messages.error(request, "Username has already been taken.")
        log_service.log_action(
            f"Registration failed: username '{username}' already taken.", 1, isSystem=False, isError=True)
        return redirect("register_view")

    email_response = user_service.get_user_by_email(email)
    if email_response["status"] == "SUCCESS":
        messages.error(request, "Email has already been used.")
        log_service.log_action(
            f"Registration failed: email '{email}' already used.", 1, isSystem=False, isError=True)
        return redirect("register_view")

    otp_code = generate_verification_code()
    response = user_service.insert_new_user(
        username, email, password, "member")

    if response["status"] == "SUCCESS":
        request.session["pending_user"] = email
        request.session["verification_code"] = otp_code
        request.session["code_generated_at"] = timezone.now().isoformat()
        request.session["verification_attempts"] = 0

        send_mail(
            subject="Your NeuroForum Verification Code",
            message=f"Your verification code is: {otp_code}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=True,
        )
        return redirect("email_verification")

    messages.error(request, ERR_MSG)
    log_service.log_action(
        f"Registration failed for email '{email}': unknown error occurred.", 1, isSystem=True, isError=True)
    return redirect("register_view")


# MARK: Process Update Profile
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def process_update_profile(request, context=None):

    if context is None:
        context = {}

    session_response = session_utils.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    username = utilities.sanitize_input(request.POST.get("username"))
    email = utilities.sanitize_input(request.POST.get("email"))

    user_response = user_service.get_user_by_id(context["user_info"]["UserID"])
    if user_response["status"] == "SUCCESS":
        context["user_data"] = user_response["data"]
    elif user_response["status"] == "NOT_FOUND":
        log_service.log_action(f"Failed to update user profile: User not found", context["user_info"]["UserID"], isError=True)
        messages.error(request, USER_NOT_FOUND_MSG)
    else:
        messages.error(request, ERR_MSG)
        return redirect('user_profile_view')

    if username == context["user_data"]["Username"] and email == context["user_data"]["Email"]:
        messages.error(request, "No change in username and email")
        return redirect("user_profile_view")

    username_response = user_service.get_user_by_username(username)
    if username_response["status"] == "SUCCESS" and username != context["user_data"]["Username"]:
        log_service.log_action("Failed to update user profile: Username has already been taken", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Username has already been taken.")
        return redirect("user_profile_view")

    email_response = user_service.get_user_by_email(email)
    if email_response["status"] == "SUCCESS" and email != context["user_data"]["Email"]:
        log_service.log_action("Failed to update user profile: Email has already been taken", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Email has already been used.")
        return redirect("user_profile_view")

    response = user_service.update_user_profile(
        context["user_info"]["UserID"], username, email)

    if response["status"] == "SUCCESS":
        session_utils.update_session(request, username)
        messages.success(request, "User Profile has been updated")
        return redirect("user_profile_view")
    else:
        messages.error(request, ERR_MSG)

    return redirect("user_profile_view")

# MARK: Process Change Password
# Safe: GET is used for initial render; POST is CSRF-protected and handles form submission only.
@require_http_methods(["GET", "POST"])
@csrf_protect
def process_change_password(request, context=None):
    if context is None:
        context = {}

    sess = session_utils.check_session(request)
    if sess.get("status") != "SUCCESS":
        log_service.log_action(
            "Change password failed: session expired",
            None,
            isError=True
        )
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    user_id = sess["data"]["UserID"]
    context["user_info"] = sess["data"]

    old_password     = request.POST.get("oldPassword", "")
    new_password     = request.POST.get("newPassword", "")
    confirm_password = request.POST.get("newConfirmPassword", "")

    if new_password != confirm_password:
        log_service.log_action(
            "Change password failed: new password and confirmation do not match",
            user_id,
            isError=True
        )
        messages.error(request, "New passwords do not match.")
        return redirect("user_profile_view")

    valid, error_msg = validate_password_nist(new_password)
    if not valid:
        log_service.log_action(
            f"Change password failed: invalid new password: {error_msg}",
            user_id,
            isError=True
        )
        messages.error(request, error_msg)
        return redirect("user_profile_view")

    user_resp = user_service.get_user_by_id(user_id)
    if user_resp.get("status") != "SUCCESS":
        log_service.log_action(
            "Change password failed: user not found",
            user_id,
            isError=True
        )
        messages.error(request, USER_NOT_FOUND_MSG)
        return redirect("user_profile_view")

    email = user_resp["data"].get("Email", "")

    auth = user_service.authenticate_user(email, old_password)
    status = auth.get("status")
    if status == "INVALID":
        log_service.log_action(
            "Change password failed: incorrect old password",
            user_id,
            isError=True
        )
        messages.error(request, "The old password you entered is incorrect.")
        return redirect("user_profile_view")
    if status != "SUCCESS":
        log_service.log_action(
            f"Change password failed: authenticate_user error: {auth!r}",
            user_id,
            isError=True
        )
        messages.error(request, ERR_MSG)
        return redirect("user_profile_view")
    
    upd = user_service.update_user_password(user_id, new_password)
    if upd.get("status") == "SUCCESS":
        log_service.log_action(
            "Password changed successfully",
            user_id,
            isError=False
        )
        messages.success(request, "Password has been changed.")
    else:
        log_service.log_action(
            f"Change password failed: update_user_password error: {upd!r}",
            user_id,
            isError=True
        )
        messages.error(request, ERR_MSG)

    return redirect("user_profile_view")

# MARK: Process Update User Role
def process_update_user_role(request, user_id):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    role = utilities.sanitize_input(request.POST.get("role"))
    performed_by = session_response["data"]["UserID"]

    user_response = user_service.get_user_by_id(user_id)
    if user_response["status"] == "NOT_FOUND":
        log_service.log_action(f"Failed to update user profile: User not found", performed_by, isError=True)
        messages.error(request, USER_NOT_FOUND_MSG)
        return redirect("admin_portal")
    elif user_response["status"] == "ERROR":
        messages.error(request, ERR_MSG)
        return redirect("admin_portal")

    result = user_service.update_user_role(user_id, role, performed_by)
    if result["status"] == "SUCCESS":
        username = user_response["data"]["Username"]
        messages.success(request, f"Updated role for {username} to {role}.")
    else:
        messages.error(request, ERR_MSG)

    return redirect("admin_portal")

# MARK: Process Delete User
def process_delete_user(request, user_id):
    session_response = session_utils.check_session(request)
    if session_response["status"] != "SUCCESS":
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    performed_by = session_response["data"]["UserID"]

    # Prevent self-deletion
    if str(performed_by) == str(user_id):
        log_service.log_action(f"Failed to update user profile: User tried to delete their own account", performed_by, isError=True)
        messages.error(request, "You cannot delete yourself.")
        return redirect("admin_portal")

    user_response = user_service.get_user_by_id(user_id)
    if user_response["status"] == "NOT_FOUND":
        log_service.log_action(f"Failed to update user profile: User not found", performed_by, isError=True)
        messages.error(request, USER_NOT_FOUND_MSG)
        return redirect("admin_portal")
    elif user_response["status"] == "ERROR":
        messages.error(request, ERR_MSG)
        return redirect("admin_portal")

    username = user_response["data"]["Username"]
    result = user_service.delete_user_by_id(user_id, performed_by)

    if result["status"] == "SUCCESS":
        messages.success(request, f"User '{username}' deleted successfully.")
    else:
        messages.error(request, ERR_MSG)

    return redirect("admin_portal")
