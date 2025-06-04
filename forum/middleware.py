# forum/middleware.py

from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def fetch_user_from_session(session_key):
    """
    Given a session_key (cookie value), load the corresponding Django session.
    If it contains "Username", return the real User instance. Otherwise, return None.
    """
    if not session_key:
        return None

    try:
        session = SessionStore(session_key=session_key)
    except Exception:
        return None

    username = session.get("Username")
    if not username:
        return None

    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


class SessionAuthMiddleware(BaseMiddleware):
    """
    ASGI middleware that:
    1. Extracts the 'sessionid' cookie from the WebSocket handshake headers.
    2. Uses fetch_user_from_session() to load session data.
    3. Sets scope['user'] = DummyUser(username) if valid, or AnonymousUser otherwise.
    """

    # async def __call__(self, scope, receive, send):
    #     # 1. Extract cookies from the headers
    #     headers = dict(scope.get("headers", []))
    #     cookies = {}
    #     if b"cookie" in headers:
    #         raw_cookies = headers[b"cookie"].decode()  # e.g. "sessionid=abc123; csrftoken=..."
    #         for part in raw_cookies.split(";"):
    #             if "=" in part:
    #                 key, val = part.strip().split("=", 1)
    #                 cookies[key] = val

    #     # 2. Get the "sessionid" cookie (default Django session name)
    #     session_key = cookies.get("sessionid")
    #     user = await fetch_user_from_session(session_key)

    #     # 3. If we got a username, wrap it in DummyUser; otherwise, AnonymousUser
    #     if user:
    #         scope["user"] = user
    #     else:
    #         scope["user"] = AnonymousUser()

    #     # 4. Proceed down the ASGI stack (to your consumer)
    #     return await super().__call__(scope, receive, send)

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        cookies = {}
        if b"cookie" in headers:
            raw_cookies = headers[b"cookie"].decode()
            print("🍪 Raw cookies:", raw_cookies)
            for part in raw_cookies.split(";"):
                if "=" in part:
                    key, val = part.strip().split("=", 1)
                    cookies[key] = val

        session_key = cookies.get("sessionid")
        print("🔑 sessionid from cookie:", session_key)

        user = await fetch_user_from_session(session_key)

        if user:
            print("✅ User resolved:", user.username)
            scope["user"] = user
        else:
            print("❌ Anonymous user assigned")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

