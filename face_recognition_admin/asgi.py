import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import faceapp.routing  # Ensure this file exists and includes `websocket_urlpatterns`

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_recognition_admin.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            faceapp.routing.websocket_urlpatterns  # Make sure this is correctly set in routing.py
        )
    ),
})
