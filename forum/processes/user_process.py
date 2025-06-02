from ..services import session_service
from ..services.db_services import user_service
from django.shortcuts import redirect
from django.contrib import messages

def process_login(request):
    email = request.POST.get("email")
    password = request.POST.get("password")

    result = user_service.authenticate_user(email, password)

    if result["status"] == "SUCCESS":
        session_response = session_service.setup_session(request, result["data"])
        if session_response["status"] == "SUCCESS":
            return redirect("index")

    if result["status"] == "NOT_FOUND" or result["status"] == "INVALID":
        messages.error(request, "Invalid email or password. Please try again.")
        return redirect("login_view")

    messages.error(request, "A problem has occurred. Please try again.")
    return redirect("login_view")


def process_register(request):
    username = request.POST.get("username")
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirmPassword = request.POST.get("confirmPassword")

    response = user_service.insert_new_user(username, email, password, "member", "test")

    if response["status"] == "SUCCESS":
        return redirect("login_view")
    
    messages.error(request, "A problem has occurred. Please try again.")
    return redirect("register_view")
