from star_api import consumers
from django.urls import re_path


websocket_urlpatterns = [
    re_path('^server/$', consumers.ServiceData.as_asgi())
]
