
from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("", views.community_dashboard, name="dashboard"),

    # Notices
    path("notices/create/", views.create_notice, name="notice_create"),
    path("notices/<int:notice_id>/", views.notice_detail, name="notice_detail"),
    path("notices/<int:notice_id>/edit/", views.edit_notice, name="notice_edit"),
    path("notices/<int:notice_id>/delete/", views.delete_notice, name="notice_delete"),

    # Events
    path("events/create/", views.create_event, name="event_create"),
    path("events/<int:event_id>/", views.event_detail, name="event_detail"),
    path("events/<int:event_id>/edit/", views.edit_event, name="event_edit"),
    path("events/<int:event_id>/delete/", views.delete_event, name="event_delete"),

    # Deliveries
    path("deliveries/", views.deliveries, name="deliveries"),
    path("deliveries/create/", views.create_delivery, name="delivery_create"),
    path("deliveries/<int:delivery_id>/", views.delivery_detail, name="delivery_detail"),

    
# Incidents
path("incidents/", views.incidents, name="incidents"),
path("incidents/create/", views.create_incident, name="incident_create"),
path(
    "incidents/<int:incident_id>/",
    views.incident_detail,
    name="incident_detail",
),


# Vehicle and service personnel logs
path("gate-logs/", views.gate_logs, name="gate_logs"),
path("gate-logs/create/", views.create_gate_entry, name="gate_entry_create"),
path(
    "gate-logs/<int:entry_id>/",
    views.gate_entry_detail,
    name="gate_entry_detail",
),


# Maintenance dues and payments
path("maintenance-dues/", views.maintenance_dues, name="maintenance_dues"),
path(
    "maintenance-dues/create/",
    views.create_maintenance_charge,
    name="maintenance_charge_create",
),
path(
    "maintenance-dues/<int:charge_id>/",
    views.maintenance_charge_detail,
    name="maintenance_charge_detail",
),
path(
    "maintenance-dues/<int:charge_id>/record-payment/",
    views.record_maintenance_payment,
    name="maintenance_payment_create",
),

path("notifications/", views.notifications, name="notifications"),
path(
    "notifications/read-all/",
    views.mark_all_notifications_read,
    name="mark_all_notifications_read",
),
path(
    "notifications/<int:notification_id>/mark-read/",
    views.mark_notification_read,
    name="mark_notification_read",
),
path(
    "notifications/<int:notification_id>/",
    views.notification_open,
    name="notification_open",
),

path(
    "reports/",
    views.management_reports,
    name="management_reports",
),
]
