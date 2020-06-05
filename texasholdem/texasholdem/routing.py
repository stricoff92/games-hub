
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import lobby.routing
import connectquatro.routing

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            lobby.routing.websocket_urlpatterns
            + connectquatro.routing.websocket_urlpatterns
        )
    ),
})
