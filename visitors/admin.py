
from django.contrib import admin
from .models import VisitorInvitation, VisitorLog


@admin.register(VisitorInvitation)
class VisitorInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "visitor_name",
        "resident",
        "visitor_phone",
        "expected_at",
        "status",
        "reviewed_by",
        "created_at",
    )

    list_filter = ("status", "expected_at", "created_at")
    search_fields = (
        "visitor_name",
        "visitor_phone",
        "resident__user__username",
        "resident__user__first_name",
        "resident__user__last_name",
    )

    readonly_fields = ("created_at", "updated_at", "reviewed_at")

    autocomplete_fields = ("resident", "reviewed_by")

    date_hierarchy = "expected_at"
    list_per_page = 25


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = (
        "visitor_name",
        "resident",
        "entry_at",
        "exit_at",
        "checked_in_by",
        "checked_out_by",
    )

    list_filter = ("entry_at", "exit_at", "created_at")

    search_fields = (
        "visitor_name",
        "visitor_phone",
        "resident__user__username",
        "resident__user__first_name",
        "resident__user__last_name",
    )

    readonly_fields = ("created_at",)

    autocomplete_fields = (
        "invitation",
        "resident",
        "checked_in_by",
        "checked_out_by",
    )

    date_hierarchy = "created_at"
    list_per_page = 25
