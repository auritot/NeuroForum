from ..services import session_service
from ..services.db_services import post_service, log_service
from django.shortcuts import redirect
from django.contrib import messages

ERR_MSG = "A problem has occurred. Please try again."
SESSION_EXPIRED_MSG = "Session Expired! Please login again."

# MARK: Insert Post
def process_create_post(request, context=None):

    if context is None:
        context = {}

    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")

    postTitle = request.POST.get("postTitle", "")
    postDescription = request.POST.get("postDescription", "")
    allowComments = request.POST.get("allowComments") == "on"

    if not postTitle or not postDescription:
        log_service.log_action("Failed to create post: User left post title or description empty", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Post title or description cannot be empty!")
        return redirect("index")

    response = post_service.insert_new_post(
        postTitle, postDescription, allowComments, context["user_info"]["UserID"]
    )

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=response["data"]["post_id"])
    else: 
        messages.error(request, ERR_MSG)
        return redirect("index")

# MARK: Delete Post by ID
def process_delete_post(request, post_id, context=None):

    if context is None:
        context = {}

    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")
    
    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]
    else: 
        messages.error(request, ERR_MSG)
        return redirect('index')

    if context["post"]["UserID_id"] == context["user_info"]["UserID"]:
        response = post_service.delete_post_by_id(post_id, context["user_info"]["UserID"])
    elif context["user_info"]["Role"] == "admin":
        response = post_service.delete_post_by_id(post_id, context["user_info"]["UserID"], isAdmin=True)
    else: 
        log_service.log_action(f"Failed to delete Post {post_id}: User was unauthorized", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Unauthorized to delete the post")
        return redirect('index')

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('index')
    else:
        messages.error(request, ERR_MSG)
        if context["user_info"]["Role"] == "admin": return redirect('admin_manage_post_view')
        else: return redirect('post_view', post_id=post_id)

# MARK: Update Post by ID
def process_update_post(request, post_id, context=None):

    if context is None:
        context = {}

    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, SESSION_EXPIRED_MSG)
        return redirect("login_view")
        
    postTitle = request.POST.get("postTitle")
    postDescription = request.POST.get("postDescription")
    allowComments = request.POST.get("allowComments") == "on"

    if not postTitle or not postDescription:
        log_service.log_action(f"Failed to update Post {post_id}: User left post title or description empty", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Post title or description cannot be empty!")
        return redirect("index")

    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]
    else: 
        messages.error(request, ERR_MSG)
        return redirect('index')

    if context["post"]["UserID_id"] == context["user_info"]["UserID"]:        
        response = post_service.update_post_by_id(postTitle, postDescription, allowComments, post_id, context["user_info"]["UserID"])
    else: 
        log_service.log_action(f"Failed to update Post {post_id}: User was unauthorized", context["user_info"]["UserID"], isError=True)
        messages.error(request, "Unauthorized to update the post")
        return redirect('index')
    
    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=post_id)
    else:
        messages.error(request, ERR_MSG)
        return redirect('post_view', post_id=post_id)
