from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

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
            return UserAccount.objects.get(Username__iexact=username)
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
            print(f"✅ Real user resolved from session: {user.Username}")
            scope["user"] = user
        else:
            print("❌ Anonymous user assigned (invalid session or no Username)")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

class IPBanMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = self.get_client_ip(request)
        if cache.get(f"login_ban_{ip}"):
            return redirect("banned_view")  # Named URL

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get("REMOTE_ADDR")