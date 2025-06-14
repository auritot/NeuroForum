import requests
from ..services import session_service, utilities
from ..services.db_services import user_service
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings


def process_login(request):
    if request.method != 'POST':
        return redirect('login_view')

    email = utilities.sanitize_input(request.POST.get("email"))
    password = utilities.sanitize_input(request.POST.get("password"))

    if not utilities.validate_email(email):
        messages.error(request, "Enter a valid email.")
        return redirect("login_view")

    result = user_service.authenticate_user(email, password)

    if result["status"] == "SUCCESS":
        session_response = session_service.setup_session(
            request, result["data"])
        if session_response["status"] == "SUCCESS":
            return redirect("index")

    if result["status"] == "NOT_FOUND" or result["status"] == "INVALID":
        messages.error(request, "Invalid email or password.")
        return redirect("login_view")

    messages.error(request, "A problem has occurred. Please try again.")
    return redirect("login_view")


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
                # Optional but recommended
                'remoteip': request.META.get('REMOTE_ADDR')
            }, timeout=5)  # Set a timeout for the request

            result = response.json()

            if not result.get('success'):
                recaptcha_error_message = "CAPTCHA verification failed. Please try again."
                print(
                    f"reCAPTCHA error codes from Google: {result.get('error-codes')}")

        except requests.exceptions.RequestException as e:
            recaptcha_error_message = "Could not verify CAPTCHA due to a network error. Please try again."
            print(f"reCAPTCHA API request failed: {e}")

    # If reCAPTCHA verification failed, add message and redirect
    if recaptcha_error_message:
        messages.error(request, recaptcha_error_message)
        return redirect("register_view")

    if confirmPassword != password:
        messages.error(request, "Passwords does not match.")
        return redirect("register_view")

    if not utilities.validate_email(email):
        messages.error(request, "Enter a valid email.")
        return redirect("register_view")

    username_response = user_service.get_user_by_username(username)
    if username_response["status"] == "SUCCESS":
        messages.error(request, "Username has already been taken.")
        return redirect("register_view")

    email_response = user_service.get_user_by_email(email)
    if email_response["status"] == "SUCCESS":
        messages.error(request, "Email has already been used.")
        return redirect("register_view")

    response = user_service.insert_new_user(
        username, email, password, "member", "test")

    if response["status"] == "SUCCESS":
        return redirect("login_view")

    messages.error(request, "A problem has occurred. Please try again.")
    return redirect("register_view")
