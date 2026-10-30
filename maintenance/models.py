from django.db import models

# Create your models here.

from django.conf import settings
from django.db import models


class MaintenanceRequest(models.Model):

    class Category(models.TextChoices):
        PLUMBING = "PLUMBING", "Plumbing"
        ELECTRICAL = "ELECTRICAL", "Electrical"
        CLEANING = "CLEANING", "Cleaning"
        LIFT = "LIFT", "Lift"
        WATER = "WATER", "Water Supply"
        SECURITY = "SECURITY", "Security"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ON_HOLD = "ON_HOLD", "On Hold"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    resident = models.ForeignKey(
        "residents.ResidentProfile",
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
    )

    title = models.CharField(max_length=150)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    description = models.TextField()
    location = models.CharField(
        max_length=150,
        help_text="For example, Flat A-101 or the second-floor corridor.",
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_maintenance_requests",
    )

    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"MR-{self.pk}: {self.title}"

    @property
    def is_open(self):
        return self.status not in {
            self.Status.RESOLVED,
            self.Status.CLOSED,
        }
