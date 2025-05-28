from django.shortcuts import render, redirect

from .models import UserAccount
from .services import db_service, session_service


# Create your views here.
# MARK: Index Page
def index(request):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        return render(
            request, "html/index.html", {"user_info": session_response["data"]}
        )

    return render(request, "html/index.html")


# MARK: Login Page
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        result = db_service.authenticate_user(email, password)

        if result["status"] == "SUCCESS":
            session_response = session_service.setup_session(request, result["data"])
            if session_response["status"] == "SUCCESS":
                return redirect("index")
            else:
                return redirect("login_view")

        if result["status"] == "NOTFOUND" or result["status"] == "INVALID":
            return redirect("login_view")

        else:
            print(result["message"])

    else:
        return render(
            request,
            "html/login_view.html",
            {"error": "Invalid email or password. Please try again."},
        )

    return render(request, "html/login_view.html")


# MARK: Register Page
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmPassword = request.POST.get("confirmPassword")

        response = db_service.insert_new_user(
            username, email, password, "member", "test"
        )

        if response["status"] == "SUCCESS":
            return redirect("login_view")

        else:
            return render(request, "html/register_view.html")

    return render(request, "html/register_view.html")
