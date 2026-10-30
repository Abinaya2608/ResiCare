
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Apartment, ResidentProfile


class ResidentProfileInlineFormSet(BaseInlineFormSet):
    """Prevent assigning non-resident accounts to resident profiles."""

    def clean(self):
        super().clean()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE", False):
                continue

            user = form.cleaned_data.get("user")

            if user and user.role != user.Role.RESIDENT:
                raise ValidationError(
                    f"{user.username} does not have the Resident role."
                )


class ResidentProfileInline(admin.TabularInline):
    model = ResidentProfile
    formset = ResidentProfileInlineFormSet
    extra = 0
    fields = (
        "user",
        "resident_type",
        "move_in_date",
        "emergency_contact_name",
        "emergency_contact_phone",
    )
    autocomplete_fields = ("user",)
    show_change_link = True


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = (
        "building_name",
        "unit_number",
        "floor_number",
        "bedrooms",
        "monthly_maintenance",
        "is_active",
        "occupied",
    )
    list_filter = ("building_name", "floor_number", "bedrooms", "is_active")
    search_fields = ("building_name", "unit_number")
    ordering = ("building_name", "unit_number")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (ResidentProfileInline,)

    fieldsets = (
        (
            "Apartment Information",
            {
                "fields": (
                    "building_name",
                    "unit_number",
                    "floor_number",
                    "bedrooms",
                    "area_sqft",
                )
            },
        ),
        (
            "Maintenance",
            {
                "fields": ("monthly_maintenance", "is_active")
            },
        ),
        (
            "Record Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ResidentProfile)
class ResidentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "apartment",
        "resident_type",
        "move_in_date",
    )
    list_filter = ("resident_type", "apartment__building_name")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "apartment__unit_number",
        "emergency_contact_name",
    )
    autocomplete_fields = ("user", "apartment")
    list_select_related = ("user", "apartment")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Resident Account",
            {"fields": ("user", "apartment", "resident_type", "move_in_date")},
        ),
        (
            "Emergency Contact",
            {
                "fields": (
                    "emergency_contact_name",
                    "emergency_contact_phone",
                )
            },
        ),
        (
            "Record Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
