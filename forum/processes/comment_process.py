from ..services import session_service
from ..services.db_services import comment_service, log_service
from django.shortcuts import redirect
from django.contrib import messages

SESSION_EXPIRED_MSG = "Session Expired! Please login again."
ERROR_MSG = "A problem has occurred. Please try again."

# MARK: Insert Comment
def process_create_comment(request, post_id, context=None):

    if context is None:
        context = {}

    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    commentText = request.POST.get("commentText", "")
    if not commentText:
        log_service.log_action(f"Failed to create comment in Post {post_id}: User left comment text empty", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Comment cannot be empty!")
        return redirect('post_view', post_id=post_id)

    response = comment_service.insert_new_comment(commentText, post_id, context["user_info"]["UserID"])

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=post_id)
    else: 
        messages.error(request, ERROR_MSG)
        return redirect('post_view', post_id=post_id)

# MARK: Delete Comment by ID
def process_delete_comment(request, post_id, comment_id, context=None):

    if context is None:
        context = {}

    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    comment_response = comment_service.get_comment_by_id(comment_id)
    if comment_response["status"] == "SUCCESS":
        context["comment"] = comment_response["data"]["comment"]
    else: 
        messages.error(request, ERROR_MSG)
        return redirect('index')

    if context["comment"]["UserID_id"] == context["user_info"]["UserID"]:
        response = comment_service.delete_comment_by_id(post_id, comment_id, context["user_info"]["UserID"])
    elif context["user_info"]["Role"] == "admin":
        response = comment_service.delete_comment_by_id(post_id, comment_id, context["user_info"]["UserID"], isAdmin=True)
    else: 
        log_service.log_action(f"Failed to delete Comment {comment_id} in Post {post_id}: User was unauthorized", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Unauthorized to delete this comment")
        return redirect('index')

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=post_id)
    else:
        messages.error(request, ERROR_MSG)
        return redirect('index')

# MARK: Update Comment by ID
def process_update_comment(request, post_id, comment_id, context=None):

    if context is None:
        context = {}

    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    comment_response = comment_service.get_comment_by_id(comment_id)
    if comment_response["status"] == "SUCCESS":
        context["comment"] = comment_response["data"]["comment"]
    else:
        messages.error(request, ERROR_MSG)
        return redirect('index')
    
    comment_url = f"post_view/{context["comment"]["PostID_id"]}?page={context["comment"]["PageNumberInPost"]}#comment-{context["comment"]["CommentPosition"]}"

    editCommentText = request.POST.get("editCommentText")
    if not editCommentText: 
        log_service.log_action(f"Failed to update Comment in Post {post_id}: User left comment text empty", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Comment cannot be empty!")
        redirect(comment_url)

    if context["comment"]["UserID_id"] == context["user_info"]["UserID"]:
        response = comment_service.update_comment_by_id(editCommentText, comment_id, post_id, context["user_info"]["UserID"])
    else: 
        log_service.log_action(f"Failed to update Comment {comment_id} in Post {post_id}: User was unauthorized", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Unauthorized to update the comment")
        return redirect('post_view', post_id=post_id)

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        redirect(comment_url)
    else:
        messages.error(request, ERROR_MSG)
        return redirect('post_view', post_id=post_id)
