
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone


class VisitorInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    resident = models.ForeignKey(
        "residents.ResidentProfile",
        on_delete=models.PROTECT,
        related_name="visitor_invitations",
    )

    visitor_name = models.CharField(max_length=100)

    visitor_phone = models.CharField(
        max_length=15,
        validators=[MinLengthValidator(7)],
    )

    purpose = models.CharField(max_length=250)

    expected_at = models.DateTimeField()

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_visitor_invitations",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.visitor_name} - {self.get_status_display()}"

    @property
    def is_upcoming(self):
        return (
            self.expected_at >= timezone.now()
            and self.status == self.Status.APPROVED
        )


class VisitorLog(models.Model):
    # An invitation is optional so security can register walk-in visitors.
    invitation = models.ForeignKey(
        VisitorInvitation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visit_logs",
    )

    resident = models.ForeignKey(
        "residents.ResidentProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="visitor_logs",
    )

    visitor_name = models.CharField(max_length=100)

    visitor_phone = models.CharField(max_length=15)

    purpose = models.CharField(max_length=250)

    entry_at = models.DateTimeField(null=True, blank=True)

    exit_at = models.DateTimeField(null=True, blank=True)

    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitor_checkins",
    )

    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitor_checkouts",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.visitor_name} - {self.entry_at or 'Not checked in'}"

    @property
    def is_inside(self):
        return self.entry_at is not None and self.exit_at is None
