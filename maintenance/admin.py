
from django.contrib import admin

from .models import MaintenanceRequest


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "resident",
        "category",
        "priority",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "category",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "location",
        "resident__user__username",
        "resident__user__first_name",
        "resident__user__last_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "resolved_at",
    )
    autocomplete_fields = ("resident", "assigned_to")
    list_per_page = 25
    date_hierarchy = "created_at"
