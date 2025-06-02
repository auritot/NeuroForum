from ..services import session_service
from ..services.db_services import post_service
from .. import views


def process_create_post(request):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]

    postTitle = request.POST.get("postTitle")
    postDescription = request.POST.get("postDescription")
    allowComments = request.POST.get("allowComments") == "on"

    response = post_service.insert_new_post(
        postTitle, postDescription, allowComments, context["UserID"]
    )

    if response["status"] == "SUCCESS":
        return views.index(request)

    return views.index(request)
