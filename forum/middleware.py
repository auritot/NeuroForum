from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from forum.ip_utils import get_client_ip
from forum.models import UserAccount
from forum.services.db_services.custom_session_service import CustomSessionService
from asgiref.sync import sync_to_async

@database_sync_to_async
def fetch_user_from_session(session_key):
    if not session_key:
        return None

    try:
        session = SessionStore(session_key=session_key)
        username = session.get("Username", "").strip()

        if not username:
            return None

        # Case-insensitive match
        try:
            return UserAccount.objects.get(Username__iexact=username)
        except UserAccount.DoesNotExist:

            return None

    except Exception as e:
        return None

class SessionAuthMiddleware(BaseMiddleware):
    """
    Channels middleware that first tries your custom_sessionid cookie,
    then falls back to Django's standard sessionid.
    """
    async def __call__(self, scope, receive, send):
        # 1) parse cookies
        headers = dict(scope.get("headers", []))
        cookies = {}
        if b"cookie" in headers:
            for part in headers[b"cookie"].decode().split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    cookies[k] = v

        user = None

        # 2) try your custom session
        custom_key = cookies.get("custom_sessionid")
        if custom_key:
            service = CustomSessionService()
            data = await sync_to_async(service.load)(custom_key)
            username = (data or {}).get("Username", "").strip()
            if username:
                try:
                    user = await database_sync_to_async(
                        UserAccount.objects.get
                    )(Username__iexact=username)
                except UserAccount.DoesNotExist:
                    user = None

        # 3) fallback to Django session if still none
        if user is None:
            django_key = cookies.get("sessionid")
            user = await fetch_user_from_session(django_key)

        scope["user"] = user or AnonymousUser()
        return await super().__call__(scope, receive, send)

class IPBanMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = get_client_ip(request)

        if cache.get(f"login_ban_{ip}"):
            # Allow access to the banned page itself
            if request.path != '/banned/' and not request.path.startswith('/static/'):
                return redirect("banned_view")
        