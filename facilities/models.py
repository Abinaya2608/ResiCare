from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Facility(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField()
    location = models.CharField(max_length=150)
    capacity = models.PositiveIntegerField(default=10)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.opening_time and self.closing_time:
            if self.closing_time <= self.opening_time:
                raise ValidationError(
                    {"closing_time": "Closing time must be later than opening time."}
                )


class FacilityBooking(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    resident = models.ForeignKey(
        "residents.ResidentProfile",
        on_delete=models.PROTECT,
        related_name="facility_bookings",
    )
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    purpose = models.CharField(max_length=250)

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_facility_bookings",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    management_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-booking_date", "start_time"]
        indexes = [
            models.Index(fields=["facility", "booking_date", "status"]),
            models.Index(fields=["resident", "booking_date"]),
        ]

    def __str__(self):
        return f"{self.facility.name} - {self.booking_date} - {self.resident}"

    def clean(self):
        errors = {}
        if self.facility_id and not self.facility.is_active:
            errors["facility"] = (
        "This facility is currently unavailable for booking."
        )
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                errors["end_time"] = "End time must be later than start time."

        if self.booking_date and self.booking_date < timezone.localdate():
            errors["booking_date"] = "Choose today or a future date."

        if self.facility_id and self.start_time and self.end_time:
            facility = self.facility

            if (
                self.start_time < facility.opening_time
                or self.end_time > facility.closing_time
            ):
                errors["start_time"] = (
                    f"Choose a time within the facility's operating hours "
                    f"({facility.opening_time.strftime('%H:%M')}–"
                    f"{facility.closing_time.strftime('%H:%M')})."
                )

        if (
            self.status == self.Status.APPROVED
            and self.facility_id
            and self.booking_date
            and self.start_time
            and self.end_time
        ):
            conflicts = FacilityBooking.objects.filter(
                facility_id=self.facility_id,
                booking_date=self.booking_date,
                status=self.Status.APPROVED,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )

            if self.pk:
                conflicts = conflicts.exclude(pk=self.pk)

            if conflicts.exists():
                errors["start_time"] = (
                    "This time overlaps an existing approved booking."
                )

        if errors:
            raise ValidationError(errors)
