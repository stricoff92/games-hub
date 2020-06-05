
from django.conf.urls import url, include
from connectquatro import views

urlpatterns = [
    url(r"connectquat/ping/$", views.ping, name="api-connectquat-ping"),
    url(r"connectquat/move/$", views.make_move, name="api-connectquat-move"),
    url(r"connectquat/(?P<slug>[0-9a-zA-Z]+)/$", views.game_page, name="page-connectquat"),
]
