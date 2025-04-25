# chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/video/(?P<room_name>\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/$', consumers.VideoChatConsumer.as_asgi()),
]
