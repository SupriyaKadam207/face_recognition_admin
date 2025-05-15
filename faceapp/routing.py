# faceapp/routing.py
from django.urls import re_path
from faceapp.consumers import VideoFeedConsumer  # Explicit import

# Define WebSocket URL patterns
websocket_urlpatterns = [
    re_path(r'^ws/video_feed/$', VideoFeedConsumer.as_asgi()),  # WebSocket path for video feed
]
