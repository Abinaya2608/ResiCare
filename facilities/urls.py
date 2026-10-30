
from django.urls import path

from . import views

app_name = "facilities"

urlpatterns = [
    path("", views.facility_dashboard, name="dashboard"),
    path("book/", views.create_booking, name="create_booking"),
    path(
        "booking/<int:booking_id>/",
        views.booking_detail,
        name="booking_detail",
    ),
]
