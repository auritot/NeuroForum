from ..services import session_service
from ..services.db_services import post_service
from django.shortcuts import redirect
from django.contrib import messages

# MARK: Insert Post
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
        return redirect("index")

    return redirect("index")

# MARK: Delete Post by ID
def process_delete_post(request, post_id):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]

    response = post_service.delete_post_by_id(post_id)

    if response["status"] == "SUCCESS":
        return redirect('index')

    return redirect('index')

# MARK: Update Post by ID
def process_update_post(request, post_id):
    session_response = session_service.check_session(request)

    if session_response["status"] == "SUCCESS":
        context = session_response["data"]
        
    postTitle = request.POST.get("postTitle")
    postDescription = request.POST.get("postDescription")
    allowComments = request.POST.get("allowComments") == "on"

    response = post_service.update_post_by_id(postTitle, postDescription, allowComments, post_id)

    if response["status"] == "SUCCESS":
        return redirect('post_view', post_id=post_id)

    return redirect('post_view', post_id=post_id)