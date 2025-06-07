from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings

from .services import session_service, utilities
from .services.db_services import post_service, comment_service, ContentFiltering_service
from django.contrib.messages import get_messages

# Create your views here.
# MARK: Index View
def index(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    total_post_count = 0

    post_count_response = post_service.get_total_post_count()
    if post_count_response["status"] == "SUCCESS":
        # total_post_count: int = post_count_response["data"]["total_post_count"]
        total_post_count = post_count_response["data"]["total_post_count"]

    pagination_data = utilities.get_pagination_data(current_page, per_page, total_post_count)

    posts_response = post_service.get_posts_for_page(pagination_data["start_index"], per_page)
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


# MARK: Register View
def register_view(request, context={}):
    messages = get_messages(request)
    for message in messages:
        context["error"] = message
        
    return render(request, "html/register_view.html", context)


# MARK: Post Form View
def post_form_view(request, context={}, post_id=None):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    
    if post_id != None:
        post_response = post_service.get_post_by_id(post_id)
        if post_response["status"] == "SUCCESS":
            context["post"] = post_response["data"]["post"]

    return render(request, "html/post_form_view.html", context)

def filtered_words_api(request):
    response = ContentFiltering_service.get_all_filtered_words()
    return JsonResponse(response["data"], safe=False)

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

    pagination_data = utilities.get_pagination_data(current_page, per_page, total_comment_count)

    comments_response = comment_service.get_comments_for_page(pagination_data["start_index"], per_page, postID=post_id)
    if comments_response["status"] == "SUCCESS":
        context["comments"] = comments_response["data"]["comments"]

    context.update(pagination_data)

    return render(request, "html/post_view.html", context)


# MARK: User Profile View
def user_profile_view(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    return render(request, "html/user_profile_view.html", context)

# MARK: User Manage Post View
def user_manage_post_view(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    per_page = 10
    current_page = int(request.GET.get("page", 1))

    post_count_response = post_service.get_total_post_count(userID=context["user_info"]["UserID"])
    if post_count_response["status"] == "SUCCESS":
        total_post_count: int = post_count_response["data"]["total_post_count"]

    pagination_data = utilities.get_pagination_data(current_page, per_page, total_post_count)
    
    posts_response = post_service.get_posts_for_page(pagination_data["start_index"], per_page, userID=context["user_info"]["UserID"])
    if posts_response["status"] == "SUCCESS":
        context["posts"] = posts_response["data"]["posts"]

    context.update(pagination_data)

    return render(request, "html/user_manage_post_view.html", context)

# MARK: User Manage Comment View
def user_manage_comment_view(request, context={}):
    session_response = session_service.check_session(request)
    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]

    per_page = 2
    current_page = int(request.GET.get("page", 1))

    comment_count_response = comment_service.get_total_comment_count_by_user_id(context["user_info"]["UserID"])
    if comment_count_response["status"] == "SUCCESS":
        total_comment_count: int = comment_count_response["data"]["total_comment_count"]

    pagination_data = utilities.get_pagination_data(current_page, per_page, total_comment_count)
    
    comments_response = comment_service.get_comments_for_page(pagination_data["start_index"], per_page, userID=context["user_info"]["UserID"])
    if comments_response["status"] == "SUCCESS":
        context["comments"] = comments_response["data"]["comments"]

    context.update(pagination_data)

    return render(request, "html/user_manage_comment_view.html", context)

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

# MARK: Chat View
def chat_view(request, other_user):
    print("🌐 HTTP session:", dict(request.session.items()))
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
