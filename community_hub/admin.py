
from django.contrib import admin
from .models import Notice, CommunityEvent, IncidentReport, AppNotification


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "severity",
        "status",
        "reported_by",
        "assigned_to",
        "created_at",
    )
    list_filter = ("category", "severity", "status", "created_at")
    search_fields = (
        "title",
        "location",
        "description",
        "reported_by__username",
        "assigned_to__username",
    )
    readonly_fields = ("created_at", "updated_at", "resolved_at")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "is_published", "author", "created_at")
    list_filter = ("audience", "is_published", "created_at")
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CommunityEvent)
class CommunityEventAdmin(admin.ModelAdmin):
    list_display = ("title", "venue", "starts_at", "audience", "is_published")
    list_filter = ("audience", "is_published", "starts_at")
    search_fields = ("title", "description", "venue")
    readonly_fields = ("created_at", "updated_at")


from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "sender_name",
        "resident",
        "tracking_number",
        "status",
        "received_at",
        "collected_at",
    )
    list_filter = ("status", "received_at", "collected_at")
    search_fields = (
        "sender_name",
        "tracking_number",
        "description",
        "resident__user__username",
        "resident__user__first_name",
        "resident__user__last_name",
    )
    readonly_fields = (
        "received_at",
        "notified_at",
        "collected_at",
    )


from .models import GateEntry


@admin.register(GateEntry)
class GateEntryAdmin(admin.ModelAdmin):
    list_display = (
        "person_name",
        "entry_type",
        "vehicle_number",
        "purpose",
        "status",
        "entry_time",
        "exit_time",
    )
    list_filter = ("entry_type", "status", "entry_time")
    search_fields = (
        "person_name",
        "phone_number",
        "vehicle_number",
        "organization",
        "purpose",
    )
    readonly_fields = (
        "entry_time",
        "exit_time",
        "recorded_by",
        "exit_recorded_by",
    )


from .models import MaintenanceCharge, MaintenancePayment


@admin.register(MaintenanceCharge)
class MaintenanceChargeAdmin(admin.ModelAdmin):
    list_display = (
        "apartment",
        "billing_month",
        "amount_due",
        "due_date",
        "created_at",
    )
    list_filter = ("billing_month", "due_date")
    search_fields = ("apartment__id", "description")
    readonly_fields = ("created_at", "created_by")


@admin.register(MaintenancePayment)
class MaintenancePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "charge",
        "amount",
        "payment_method",
        "received_by",
        "received_at",
    )
    list_filter = ("payment_method", "received_at")
    search_fields = ("reference_number", "charge__description")
    readonly_fields = ("received_at", "received_by")

@admin.register(AppNotification)
class AppNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "category",
        "is_read",
        "created_at",
    )
    list_filter = ("category", "is_read", "created_at")
    search_fields = (
        "title",
        "message",
        "recipient__username",
        "recipient__email",
    )
    readonly_fields = ("created_at", "read_at")
    list_select_related = ("recipient",)