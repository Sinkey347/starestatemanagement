from django.urls import re_path
from star_api import consumers

websocket_urlpatterns = [
    re_path('^server/$', consumers.ServiceData.as_asgi())
]
