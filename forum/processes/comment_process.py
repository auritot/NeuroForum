from ..services import session_service
from ..services.db_services import comment_service
from django.shortcuts import redirect
from django.contrib import messages


# MARK: Insert Comment
def process_create_comment(request, post_id):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]

    commentText = request.POST.get("commentText")
    response = comment_service.insert_new_comment(
        commentText, post_id, context["UserID"]
    )

    if response["status"] == "SUCCESS":
        return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)

# MARK: Delete Comment by ID
def process_delete_comment(request, post_id, comment_id):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]

    response = comment_service.delete_comment_by_id(comment_id)

    if response["status"] == "SUCCESS":
        return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)

# MARK: Update Comment by ID
def process_update_comment(request, post_id, comment_id):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]

    editCommentText = request.POST.get("editCommentText")
    response = comment_service.update_comment_by_id(editCommentText, comment_id)

    if response["status"] == "SUCCESS":
        return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)