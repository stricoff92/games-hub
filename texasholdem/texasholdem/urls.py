from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls import url


urlpatterns = [
    url(r'^api-auth/', include('rest_framework.urls')),
    path('', include('lobby.urls')),
    path('', include('connectquatro.urls')),
    path('admin/', admin.site.urls),
]
