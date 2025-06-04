from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.contrib.sessions.backends.db import SessionStore

@database_sync_to_async
def fetch_user_from_session(session_key):
    from forum.models import UserAccount

    if not session_key:
        return None

    try:
        session = SessionStore(session_key=session_key)
        username = session.get("Username", "").strip()
        print("🧠 Resolving user:", username)

        if not username:
            return None

        # Case-insensitive match
        try:
            return UserAccount.objects.get(username__iexact=username)
        except UserAccount.DoesNotExist:
            print("❌ User not found in DB:", username)
            return None

    except Exception as e:
        print("❌ Session loading error:", e)
        return None

class SessionAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        cookies = {}
        if b"cookie" in headers:
            raw_cookies = headers[b"cookie"].decode()
            for part in raw_cookies.split(";"):
                if "=" in part:
                    key, val = part.strip().split("=", 1)
                    cookies[key] = val

        session_key = cookies.get("sessionid")
        user = await fetch_user_from_session(session_key)

        if user:
            print(f"✅ Real user resolved from session: {user.username}")
            scope["user"] = user
        else:
            print("❌ Anonymous user assigned (invalid session or no Username)")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
