from django.urls import path,re_path
from . import views
from . import consumers

urlpatterns = [
    # Home and Mode Selection
    path('', views.home, name='home'),

    # Text Chat Routes
    path('text_chat/', views.text_chat_page, name='text_chat_page'),
    path('find_match/', views.find_match, name='find_match'),
    path('chat/<str:room_id>/', views.chat_room, name='chat_room'),
    path('send_message/<str:room_id>/', views.send_message, name='send_message'),
    path('get_messages/<str:room_id>/', views.get_messages, name='get_messages'),
    path('skip/<str:room_id>/', views.skip_user, name='skip_user'),

    # Video Chat Routes
    path('video_chat/', views.video_chat_page, name='video_chat_page'),  # Page to start the connection
    path('find_video_match/', views.find_video_match, name='find_video_match'),  # Matchmaking endpoint
    path('video_chat_room/<str:room_id>/', views.video_chat_room, name='video_chat_room'),  # Video room after connection
    path('skip_video/<str:room_id>/', views.skip_video_partner, name='skip_video_partner'),  # Skipping the partner

]
websocket_urlpatterns = [
    re_path(r'^ws/video/(?P<room_name>\w+)/$', consumers.VideoChatConsumer.as_asgi()),
]