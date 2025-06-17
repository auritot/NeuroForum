from ..services import session_service
from ..services.db_services import comment_service
from django.shortcuts import redirect
from django.contrib import messages

# MARK: Insert Comment
def process_create_comment(request, post_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    commentText = request.POST.get("commentText")
    response = comment_service.insert_new_comment(
        commentText, post_id, context["user_info"]["UserID"]
    )

    if response["status"] == "SUCCESS":
        return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)

# MARK: Delete Comment by ID
def process_delete_comment(request, post_id, comment_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    comment_response = comment_service.get_comment_by_id(comment_id)
    if comment_response["status"] == "SUCCESS":
        context["comment"] = comment_response["data"]["comment"]

    response = comment_service.delete_comment_by_id(comment_id)

    if context["user_info"]["Role"] == "admin" or context["comment"]["UserID_id"] == context["user_info"]["UserID"]:
        if response["status"] == "SUCCESS":
            return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)

# MARK: Update Comment by ID
def process_update_comment(request, post_id, comment_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    editCommentText = request.POST.get("editCommentText")

    comment_response = comment_service.get_comment_by_id(comment_id)
    if comment_response["status"] == "SUCCESS":
        context["comment"] = comment_response["data"]["comment"]

    if context["user_info"]["Role"] == "admin" or context["comment"]["UserID_id"] == context["user_info"]["UserID"]:
        response = comment_service.update_comment_by_id(editCommentText, comment_id)

        if response["status"] == "SUCCESS":
            return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)