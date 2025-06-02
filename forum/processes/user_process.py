from ..services import session_service
from ..services.db_services import user_service
from .. import views


def process_login(request):
    email = request.POST.get("email")
    password = request.POST.get("password")

    result = user_service.authenticate_user(email, password)

    if result["status"] == "SUCCESS":
        session_response = session_service.setup_session(request, result["data"])
        if session_response["status"] == "SUCCESS":
            return views.index(request)

    if result["status"] == "NOT_FOUND" or result["status"] == "INVALID":
        context = {"error": "Invalid email or password. Please try again."}
        return views.login_view(request, context)

    context = {"error": "A problem has occurred. Please try again."}
    return views.login_view(request, context)


def process_register(request):
    username = request.POST.get("username")
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirmPassword = request.POST.get("confirmPassword")

    response = user_service.insert_new_user(username, email, password, "member", "test")

    if response["status"] == "SUCCESS":
        return views.login_view(request)

    context = {"error": "A problem has occurred. Please try again."}
    return views.register_view(request, context)
