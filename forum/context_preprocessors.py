from .models import ChatRoom

def chat_partners_processor(request):
    if request.session.get("Username"):
        username = request.session["Username"]
        partners = ChatRoom.get_recent_partners_for_user(username)
        return {"chat_partners": partners}
    return {"chat_partners": []}
