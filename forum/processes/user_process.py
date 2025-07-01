import requests
from ..services import session_service, utilities
from ..services.db_services import user_service, log_service
from forum.pwd_utils import validate_password_nist
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
import random
import string
from django.core.mail import send_mail
from django.utils import timezone


def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# MARK: Process Login


def process_login(request):
    if request.method != 'POST':
        return redirect('login_view')

    email = utilities.sanitize_input(request.POST.get("email"))
    password = request.POST.get("password", "")

    if not utilities.validate_email(email):
        messages.error(request, "Enter a valid email.")
        log_service.log_action(
            f"Login failed for email '{email}': invalid email format.", 1, isSystem=False, isError=True)
        return redirect("login_view")

    result = user_service.authenticate_user(email, password)

    if result["status"] == "SUCCESS":
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

    if result["status"] in ["NOT_FOUND", "INVALID"]:
        messages.error(request, "Invalid email or password.")
        log_service.log_action(
            f"Login failed for email '{email}': invalid email or password.", 1, isSystem=False, isError=True)
        return redirect("login_view")

    messages.error(request, "A problem has occurred. Please try again.")
    log_service.log_action(
        f"Login failed for email '{email}': unknown error occurred.", 1, isSystem=True, isError=True)
    return redirect("login_view")


# MARK: Process Register
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

    messages.error(request, "A problem has occurred. Please try again.")
    log_service.log_action(
        f"Registration failed for email '{email}': unknown error occurred.", 1, isSystem=True, isError=True)
    return redirect("register_view")


# MARK: Process Update Profile
def process_update_profile(request, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    username = utilities.sanitize_input(request.POST.get("username"))
    email = utilities.sanitize_input(request.POST.get("email"))

    user_response = user_service.get_user_by_id(context["user_info"]["UserID"])
    if user_response["status"] == "SUCCESS":
        context["user_data"] = user_response["data"]
    elif user_response["status"] == "NOT_FOUND":
        log_service.log_action(f"Failed to update user profile: User not found", context["user_info"]["UserID"], isError=True)
        messages.error(request, "User not found.")
    else:
        messages.error(request, "A problem has occurred. Please try again.")
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
        session_service.update_session(request, username)
        messages.success(request, "User Profile has been updated")
        return redirect("user_profile_view")
    else:
        messages.error(request, "A problem has occurred. Please try again.")

    return redirect("user_profile_view")

# MARK: Process Change Password
def process_change_password(request, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    oldPassword = utilities.sanitize_input(request.POST.get("oldPassword"))
    newPassword = utilities.sanitize_input(request.POST.get("newPassword"))
    newConfirmPassword = utilities.sanitize_input(request.POST.get("newConfirmPassword"))

    if newConfirmPassword != newPassword:
        log_service.log_action(f"Failed to update user profile: New password did not match", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Passwords does not match.")
        return redirect("user_profile_view")

    is_valid, error = validate_password_nist(newPassword)
    if not is_valid:
        log_service.log_action(f"Failed to update user profile: {error}", context["user_info"]["UserID"], isError=True)
        messages.error(request, error)
        return redirect("user_profile_view")

    # user_response = user_service.get_user_by_id(context["user_info"]["UserID"])
    # if user_response["status"] == "SUCCESS":
    #     context["user_data"] = user_response["data"]

    result = user_service.authenticate_user(
        context["user_data"]["Email"], oldPassword)
    
    if result["status"] == "INVALID":
        log_service.log_action(f"Failed to update user profile: Incorrect old password entered", context["user_info"]["UserID"], isError=True)
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect("user_profile_view")
    elif result["status"] == "NOT_FOUND":
        log_service.log_action(f"Failed to update user profile: User not found", context["user_info"]["UserID"], isError=True)
        messages.error(request, "User not found.")
        return redirect("user_profile_view")
    elif result["status"] == "ERROR":
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect("user_profile_view")


    response = user_service.update_user_password(
        context["user_info"]["UserID"], newPassword)

    if response["status"] == "SUCCESS":
        messages.success(request, "Password has been changed")
        return redirect("user_profile_view")
    else: 
        messages.error(request, "A problem has occurred. Please try again.")

    return redirect("user_profile_view")

# MARK: Process Update User Role
def process_update_user_role(request, user_id):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        messages.error(request, "Session expired. Please log in.")
        return redirect("login_view")

    role = utilities.sanitize_input(request.POST.get("role"))
    performed_by = session_response["data"]["UserID"]

    user_response = user_service.get_user_by_id(user_id)
    if user_response["status"] == "NOT_FOUND":
        log_service.log_action(f"Failed to update user profile: User not found", performed_by, isError=True)
        messages.error(request, "User not found.")
        return redirect("admin_portal")
    elif user_response["status"] == "ERROR":
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect("admin_portal")

    result = user_service.update_user_role(user_id, role, performed_by)
    if result["status"] == "SUCCESS":
        username = user_response["data"]["Username"]
        messages.success(request, f"Updated role for {username} to {role}.")
    else:
        messages.error(request, "A problem has occurred. Please try again.")

    return redirect("admin_portal")

# MARK: Process Delete User
def process_delete_user(request, user_id):
    session_response = session_service.check_session(request)
    if session_response["status"] != "SUCCESS":
        messages.error(request, "Session expired. Please log in.")
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
        messages.error(request, "User not found.")
        return redirect("admin_portal")
    elif user_response["status"] == "ERROR":
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect("admin_portal")

    username = user_response["data"]["Username"]
    result = user_service.delete_user_by_id(user_id, performed_by)

    if result["status"] == "SUCCESS":
        messages.success(request, f"User '{username}' deleted successfully.")
    else:
        messages.error(request, "A problem has occurred. Please try again.")

    return redirect("admin_portal")
