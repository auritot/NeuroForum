from ..services import session_service
from ..services.db_services import comment_service
from .. import views


def process_create_comment(request, post_id):
    print(post_id)
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]

    commentText = request.POST.get("commentText")

    response = comment_service.insert_new_comment(
        commentText, post_id, context["UserID"]
    )

    if response["status"] == "SUCCESS":
        return views.post_view(request, post_id)

    return views.post_view(request, post_id)
