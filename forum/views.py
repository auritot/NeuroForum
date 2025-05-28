from django.shortcuts import render, redirect

from .models import UserAccount
from . import db_service


# Create your views here.
# MARK: Index Page
def index(request):
    users = UserAccount.objects.all()
    return render(request, "html/index.html", {"users": users})


# MARK: Login Page
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        result = db_service.authenticate_user(email, password)

        print(result["message"])
        if result["status"] == "SUCCESS":
            return redirect("index")
        if result["status"] == "NOTFOUND" or result["status"] == "INVALID":
            return redirect("login_view")
        else:
            return render(
                request,
                "html/login_view.html",
                {"error": "Invalid email or password. Please try again."},
            )

    return render(request, "html/login_view.html")  # GET request


# MARK: Register Page
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmPassword = request.POST.get("confirmPassword")

        result = db_service.insert_new_user(username, email, password, "member", "test")

        print(result["message"])
        if result["status"] == "SUCCESS":
            return redirect("login_view")
        else:
            return render(request, "html/register_view.html")

    return render(request, "html/register_view.html")
