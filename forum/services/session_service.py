from django.http import JsonResponse
from . import utilities


# MARK: Create Session
def setup_session(request, user_data):
    try:
        request.session["UserID"] = user_data["UserID"]
        request.session["Role"] = user_data["Role"]
        request.session.set_expiry(3600)

        return utilities.response("SUCCESS", "Session has been created")

    except Exception as e:
        return utilities.response("ERROR", f"An error occurred: {str(e)}")


# MARK: Check Session
def check_session(request):
    try:
        if "UserID" in request.session and "Role" in request.session:
            user_info = {
                "UserID": request.session["UserID"],
                "Role": request.session["Role"],
            }

            return utilities.response("SUCCESS", "Session is active", user_info)
        else:
            return utilities.response("FAILURE", "No active session found")

    except Exception as e:
        return utilities.response("ERROR", f"An error occurred: {str(e)}")


# MARK: Clear Session
def clear_session(request):
    try:
        request.session.flush()

        return utilities.response("SUCCESS", "Session has been cleared")

    except Exception as e:
        return utilities.response(
            "ERROR", f"An error occurred while clearing the session: {str(e)}"
        )
