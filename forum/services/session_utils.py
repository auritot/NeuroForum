from django.http import JsonResponse
from . import utilities

# MARK: Create Session
def setup_session(request, user_data):
    try:
        request.custom_session["UserID"] = user_data["UserID"]
        request.custom_session["Role"] = user_data["Role"]
        request.custom_session["Username"] = user_data["Username"]

        request.custom_session["IP"] = request.META.get("REMOTE_ADDR")
        request.custom_session["UserAgent"] = request.META.get("HTTP_USER_AGENT")

        request.custom_session.set_expiry(3600)
        request.custom_session.save()

        return utilities.response("SUCCESS", "Session has been created")

    except Exception as e:
        return utilities.response("ERROR", f"An error occurred: {str(e)}")

def update_session(request, username):
    try:
        request.custom_session["Username"] = username
        request.custom_session.save()  # optional, usually auto-saved

        return utilities.response("SUCCESS", "Session values updated")

    except Exception as e:
        return utilities.response("ERROR", f"An error occurred: {str(e)}")

# MARK: Check Session
def check_session(request):
    try:
        if (
            "UserID" in request.custom_session and 
            "Role" in request.custom_session and
            request.custom_session.get("IP") == request.META.get("REMOTE_ADDR") and
            request.custom_session.get("UserAgent") == request.META.get("HTTP_USER_AGENT")
        ):
            user_info = {
                "UserID": request.custom_session["UserID"],
                "Role": request.custom_session["Role"],
                "Username": request.custom_session["Username"],
            }

            return utilities.response("SUCCESS", "Session is active", user_info)
        else:
            
            return utilities.response("FAILURE", "No active session found")

    except Exception as e:
        return utilities.response("ERROR", f"An error occurred: {str(e)}")


# MARK: Clear Session
def clear_session(request):
    try:
        request.custom_session.flush()

        return utilities.response("SUCCESS", "Session has been cleared")

    except Exception as e:
        return utilities.response(
            "ERROR", f"An error occurred while clearing the session: {str(e)}"
        )
