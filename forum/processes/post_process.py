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
        messages.error(request, "Session Expired! Please login again.")
        return redirect("login_view")

    postTitle = request.POST.get("postTitle", "")
    postDescription = request.POST.get("postDescription", "")
    allowComments = request.POST.get("allowComments") == "on"

    if not postTitle or not postDescription:
        messages.error(request, "Post title or description cannot be empty!")
        return redirect("index")

    response = post_service.insert_new_post(
        postTitle, postDescription, allowComments, context["user_info"]["UserID"]
    )

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=response["data"]["post_id"])
    else: 
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect("index")

# MARK: Delete Post by ID
def process_delete_post(request, post_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login again.")
        return redirect("login_view")
    
    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]
    else: 
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect('index')

    if context["post"]["UserID_id"] == context["user_info"]["UserID"]:
        response = post_service.delete_post_by_id(post_id, context["user_info"]["UserID"])
    elif context["user_info"]["Role"] == "admin":
        response = post_service.delete_post_by_id(post_id, context["user_info"]["UserID"], isAdmin=True)
    else: 
        messages.error(request, "Unauthorized to delete the post")
        return redirect('index')

    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=post_id)
    else:
        messages.error(request, "A problem has occurred. Please try again.")
        if context["user_info"]["Role"] == "admin": return redirect('admin_manage_post_view')
        else: return redirect('index')

# MARK: Update Post by ID
def process_update_post(request, post_id, context={}):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context["user_info"] = session_response["data"]
    else:
        messages.error(request, "Session Expired! Please login again.")
        return redirect("login_view")
        
    postTitle = request.POST.get("postTitle")
    postDescription = request.POST.get("postDescription")
    allowComments = request.POST.get("allowComments") == "on"

    if not postTitle or not postDescription:
        messages.error(request, "Post title or description cannot be empty!")
        return redirect("index")

    post_response = post_service.get_post_by_id(post_id)
    if post_response["status"] == "SUCCESS":
        context["post"] = post_response["data"]["post"]
    else: 
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect('index')

    if context["post"]["UserID_id"] == context["user_info"]["UserID"]:        
        response = post_service.update_post_by_id(postTitle, postDescription, allowComments, post_id, context["user_info"]["UserID"])
    else: 
        messages.error(request, "Unauthorized to update the post")
        return redirect('index')
    
    if response["status"] == "SUCCESS":
        messages.success(request, response["message"])
        return redirect('post_view', post_id=post_id)
    else:
        messages.error(request, "A problem has occurred. Please try again.")
        return redirect('post_view', post_id=post_id)
