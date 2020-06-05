
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'lobby/chat/?$', consumers.LobbyChatConsumer),
    re_path(r'game/chat/?$', consumers.GameLobbyChatConsumer),
    re_path(r'lobby/rooms/?$', consumers.LobbyRoomsConsumer),
]
