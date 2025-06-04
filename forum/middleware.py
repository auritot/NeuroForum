# forum/middleware.py

from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.contrib.sessions.backends.db import SessionStore

class DummyUser:
    def __init__(self, username):
        self.username = username
        self.is_authenticated = True

@database_sync_to_async
def fetch_user_from_session(session_key):
    """
    Given a session_key (cookie value), load the corresponding Django session.
    If it contains "Username", return DummyUser(username). Otherwise, return None.
    """
    if not session_key:
        return None

    # Use Django's SessionStore to load the session data by key
    try:
        session = SessionStore(session_key=session_key)
    except Exception:
        return None

    # The login view stored request.session["Username"]
    username = session.get("Username")
    if not username:
        return None

    return DummyUser(username)

class SessionAuthMiddleware(BaseMiddleware):
    """
    ASGI middleware that:
    1. Extracts the 'sessionid' cookie from the WebSocket handshake headers.
    2. Uses fetch_user_from_session() to load session data.
    3. Sets scope['user'] = DummyUser(username) if valid, or AnonymousUser otherwise.
    """

    async def __call__(self, scope, receive, send):
        # 1. Extract cookies from the headers
        headers = dict(scope.get("headers", []))
        cookies = {}
        if b"cookie" in headers:
            raw_cookies = headers[b"cookie"].decode()  # e.g. "sessionid=abc123; csrftoken=..."
            for part in raw_cookies.split(";"):
                if "=" in part:
                    key, val = part.strip().split("=", 1)
                    cookies[key] = val

        # 2. Get the "sessionid" cookie (default Django session name)
        session_key = cookies.get("sessionid")
        user = await fetch_user_from_session(session_key)

        # 3. If we got a username, wrap it in DummyUser; otherwise, AnonymousUser
        if user:
            scope["user"] = user
        else:
            scope["user"] = AnonymousUser()

        # 4. Proceed down the ASGI stack (to your consumer)
        return await super().__call__(scope, receive, send)
