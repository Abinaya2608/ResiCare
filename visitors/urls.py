
from django.urls import path

from . import views

app_name = "visitors"

urlpatterns = [
    path("", views.visitor_dashboard, name="dashboard"),
    path("invite/", views.create_invitation, name="create_invitation"),
    path(
        "invitation/<int:invitation_id>/review/",
        views.review_invitation,
        name="review_invitation",
    ),
    path(
        "invitation/<int:invitation_id>/cancel/",
        views.cancel_invitation,
        name="cancel_invitation",
    ),
    path(
        "invitation/<int:invitation_id>/check-in/",
        views.check_in_visitor,
        name="check_in",
    ),
    path(
        "log/<int:log_id>/check-out/",
        views.check_out_visitor,
        name="check_out",
    ),
    path(
        "walk-in/",
        views.walk_in_checkin,
        name="walk_in_checkin",
    ),
]
