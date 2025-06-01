from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings

from .models import UserAccount
from .services import session_service
from .services.db_services import user_service, post_service, comment_service


# Create your views here.
# MARK: Index Page
def index(request):
    session_response = session_service.check_session(request)
    context = {}

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    per_page = 10
    page_number = int(request.GET.get("page", 1))

    count_result = post_service.get_total_post_count()
    if count_result["status"] == "SUCCESS":
        total_posts = count_result["data"]["total_post"]

    start_index = (page_number - 1) * per_page
    end_index = start_index + per_page

    posts_result = post_service.get_posts_by_pages(start_index, per_page)
    if posts_result["status"] == "SUCCESS":
        posts = posts_result["data"]["posts"]

    total_pages = (total_posts + per_page - 1) // per_page
    page_range = range(1, total_pages + 1)

    previous_page = page_number - 1 if page_number > 1 else None
    next_page = page_number + 1 if page_number < total_pages else None

    context["posts"] = posts
    context["total_pages"] = total_pages
    context["page_range"] = page_range
    context["current_page"] = page_number
    context["previous_page"] = previous_page
    context["next_page"] = next_page

    return render(request, "html/index.html", context)


# MARK: Login Page
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        result = user_service.authenticate_user(email, password)

        if result["status"] == "SUCCESS":
            session_response = session_service.setup_session(request, result["data"])
            if session_response["status"] == "SUCCESS":
                return redirect("index")
            else:
                return redirect("login_view")

        if result["status"] == "NOTFOUND" or result["status"] == "INVALID":
            return render(
                request,
                "html/login_view.html",
                {"error": "Invalid email or password. Please try again."},
            )

        else:
            return render(
                request,
                "html/login_view.html",
                {"error": "A problem has occurred. Please try again."},
            )

    return render(request, "html/login_view.html")


# MARK: Register Page
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmPassword = request.POST.get("confirmPassword")

        response = user_service.insert_new_user(
            username, email, password, "member", "test"
        )

        if response["status"] == "SUCCESS":
            return redirect("login_view")

        else:
            return render(request, "html/register_view.html")

    return render(request, "html/register_view.html")


# MARK: Create Post View
def create_post_view(request):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context_data = session_response["data"]

        if request.method == "POST":
            postTitle = request.POST.get("postTitle")
            postDescription = request.POST.get("postDescription")
            allowComments = request.POST.get("allowComments") == "on"

            response = post_service.insert_new_post(
                postTitle, postDescription, allowComments, context_data["UserID"]
            )

            if response["status"] == "SUCCESS":
                return redirect("index")
            else:
                print(response["message"])
        else:
            return render(
                request,
                "html/create_post_view.html",
                {"user_info": session_response["data"]},
            )

    return render(request, "html/create_post_view.html")


# MARK: Post View
def post_view(request, post_id):
    session_response = session_service.check_session(request)
    context = {}

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    if request.method == "POST":
        commentText = request.POST.get("commentText")
        print(post_id)

        response = comment_service.insert_new_comment(
            commentText, post_id, context["user_info"]["UserID"]
        )

        if response["status"] == "SUCCESS":
            return redirect("post_view", post_id=post_id)
        else:
            print(response["message"])

    else:
        post_result = post_service.get_posts_by_id(post_id)
        if post_result["status"] == "SUCCESS":
            context["post"] = post_result["data"]["post"]

        comment_result = comment_service.get_comments_by_id(post_id)
        if comment_result["status"] == "SUCCESS":
            context["comments"] = comment_result["data"]["comments"]

    return render(request, "html/post_view.html", context)


# MARK: Mail Test


def mail_template(request):
    context = {}

    if request.method == "POST":
        address = request.POST.get("address")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if address and subject and message:
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [address])
                context["result"] = "Email sent successfully"
            except Exception as e:
                context["result"] = f"Error sending email: {e}"
        else:
            context["result"] = "All fields are required"

    return render(request, "html/mail_template.html", context)


def chat_view(request, other_user):
    session_response = session_service.check_session(request)

    if session_response["status"] != "SUCCESS":
        return redirect(f"/login/?next=/chat/{other_user}/")

    user_info = session_response["data"]
    username = user_info.get("Username", "").strip()

    if not username:
        print("[ERROR] Missing Username in session data:", user_info)
        return redirect("/login")

    return render(
        request,
        "html/chat_view.html",
        {"other_user": other_user, "user_info": user_info},
    )
