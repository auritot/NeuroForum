"""
ASGI config for neuroforum_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# 1. Set the DJANGO_SETTINGS_MODULE before any Django/Channels imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neuroforum_django.settings")

# 2. Initialize Django
import django
django.setup()

# 3. Now import Channels and your middleware/router
from channels.routing import ProtocolTypeRouter, URLRouter
from forum.middleware import SessionAuthMiddleware
from django.core.asgi import get_asgi_application
import forum.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionAuthMiddleware(
        URLRouter(forum.routing.websocket_urlpatterns)
    ),
})
