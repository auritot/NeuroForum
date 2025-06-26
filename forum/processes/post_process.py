from ..services import session_service
from ..services.db_services import post_service
from django.shortcuts import redirect
from django.contrib import messages

# MARK: Insert Post
def process_create_post(request, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")

    postTitle = request.POST.get("postTitle")
    postDescription = request.POST.get("postDescription")
    allowComments = request.POST.get("allowComments") == "on"

    response = post_service.insert_new_post(
        postTitle, postDescription, allowComments, context["user_info"]["UserID"]
    )

    if response["status"] == "SUCCESS":
        return redirect("index")

    return redirect("index")

# MARK: Delete Post by ID
def process_delete_post(request, post_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")
    
    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]

    if context["user_info"]["Role"] == "admin" or context["post"]["UserID_id"] == context["user_info"]["UserID"]:
        response = post_service.delete_post_by_id(post_id)

        if response["status"] == "SUCCESS":
            return redirect('index')

    return redirect('index')

# MARK: Update Post by ID
def process_update_post(request, post_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login.")
        return redirect("login_view")
        
    postTitle = request.POST.get("postTitle")
    postDescription = request.POST.get("postDescription")
    allowComments = request.POST.get("allowComments") == "on"

    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]

    if context["user_info"]["Role"] == "admin" or context["post"]["UserID_id"] == context["user_info"]["UserID"]:        
        response = post_service.update_post_by_id(postTitle, postDescription, allowComments, post_id)
        if response["status"] == "SUCCESS":
            return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)

