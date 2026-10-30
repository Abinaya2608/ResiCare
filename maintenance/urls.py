
from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("", views.maintenance_dashboard, name="dashboard"),
    path("create/", views.create_request, name="create_request"),
    path(
        "<int:request_id>/",
        views.request_detail,
        name="request_detail",
    ),
]
