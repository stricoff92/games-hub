
from django.conf.urls import url, include
from django.contrib.auth.decorators import login_required
from django.views.generic.base import RedirectView
from django.urls import path

from lobby import views

urlpatterns = [
    # Page routes.
    path('', RedirectView.as_view(url='/lobby/'), name='page-landing'),
    url(r"^lobby/?$", views.rooms_page, name='page-lobby-list'),
    url(r"^lobby/login/?$", views.login_page, name='page-lobby-login'),
    url(r"^lobby/register/?$", views.register, name='page-lobby-register'),
    url(r"^lobby/logout/?$", views.logout_page, name='page-lobby-logout'),
    url(r"^lobby/login/success/?$", views.login_redirect, name='page-lobby-login-redirect'),
    url(r"^lobby/game/(?P<slug>[0-9a-zA-Z]+)/", views.game_lobby_page, name='page-game-lobby'),

    # API Routes.
    url(r"api/lobby/create/?$", views.create_lobby, name='api-lobby-create'),
    url(r"api/lobby/start/?$", views.start_game, name='api-lobby-start'),
    url(r"api/lobby/join/(?P<slug>[0-9a-zA-Z]+)/", views.join_lobby, name='api-lobby-join'),
    url(r"api/lobby/leave/?$", views.leave_lobby, name='api-lobby-leave'),
    url(r"api/lobby/list/?$", views.see_lobbies, name='api-lobby-list'),
]
