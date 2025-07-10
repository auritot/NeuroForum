from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .db_services.custom_session_service import CustomSessionService
from .custom_session import CustomSession
from asgiref.sync import sync_to_async

class CustomSessionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.session_service = CustomSessionService()

    async def __call__(self, request):
        session_id = request.COOKIES.get("custom_sessionid")

        if session_id:
            print("Current cookie for session_id:", session_id)
            # data = self.session_service.load(session_id)
            data = await sync_to_async(self.session_service.load)(session_id)
            if data:
                request.custom_session = CustomSession(
                    service=self.session_service,
                    session_id=session_id,
                    initial_data=data
                )
            else:
                request.custom_session = CustomSession(
                    service=self.session_service,
                    session_id=session_id,
                    initial_data={}
                )
                request.custom_session.modified = True
        else:
            request.custom_session = CustomSession(service=self.session_service)
            request.custom_session.modified = True

        response = await self.get_response(request)

        if request.custom_session.modified:
            if not request.custom_session.session_id:
                request.custom_session.session_id = self.session_service.generate_session_id()
                request.custom_session.modified = True

            # request.custom_session.save()
            await sync_to_async(request.custom_session.save)()

            print("Saving cookie for session_id:", request.custom_session.session_id)

            response.set_cookie(
                "custom_sessionid",
                request.custom_session.session_id,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=request.custom_session._expiry_seconds
            )
            
        return response
