from django.urls import re_path

from ocpp_app.consumers import OCPPConsumer

websocket_urlpatterns = [
    re_path(r'ws/ocpp/(?P<charge_point_id>[^/]+)/$', OCPPConsumer.as_asgi()),
]
