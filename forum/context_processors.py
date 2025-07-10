from .models import ChatRoom

def chat_partners_processor(request):
    """
    Always read from our custom_session, not Django's default session.
    """
    # custom_session should have been set by CustomSessionMiddleware
    data = getattr(request, "custom_session", None)
    username = None
    if data:
        # if you're wrapping your session in a CustomSession object...
        try:
            username = data.get("Username")
        except AttributeError:
            # or if you're using a plain dict
            username = data.get("Username")
    if username:
        partners = ChatRoom.get_recent_partners_for_user(username)
        return {"chat_partners": partners}
    return {"chat_partners": []}
