from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from .services.session_service import get_session_data, get_user_model_from_username

class DummyUser:
    def __init__(self, username):
        self.username = username
        self.is_authenticated = True

@database_sync_to_async
def fetch_user_from_session(session_key):
    session_data = get_session_data(session_key)
    if not session_data or session_data.get("status") != "SUCCESS":
        return None
    username = session_data["data"].get("Username", "").strip()
    if not username:
        return None
    return DummyUser(username)

class SessionAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        cookies = {}
        if b"cookie" in headers:
            raw_cookies = headers[b"cookie"].decode()
            for part in raw_cookies.split(";"):
                if "=" in part:
                    key, val = part.strip().split("=", 1)
                    cookies[key] = val

        session_key = cookies.get("sessionid", None)
        user = None
        if session_key:
            user = await fetch_user_from_session(session_key)

        if user:
            scope["user"] = user
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)