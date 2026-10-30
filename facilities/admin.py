
from django.contrib import admin

from .models import Facility, FacilityBooking


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location",
        "capacity",
        "opening_time",
        "closing_time",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "location", "description")
    list_editable = ("is_active",)
    list_per_page = 25


@admin.register(FacilityBooking)
class FacilityBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "facility",
        "resident",
        "booking_date",
        "start_time",
        "end_time",
        "status",
        "reviewed_by",
    )
    list_filter = (
        "status",
        "booking_date",
        "facility",
    )
    search_fields = (
        "facility__name",
        "resident__user__username",
        "resident__user__first_name",
        "resident__user__last_name",
        "purpose",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "reviewed_at",
    )
    autocomplete_fields = ("facility", "resident", "reviewed_by")
    date_hierarchy = "booking_date"
    list_per_page = 25
