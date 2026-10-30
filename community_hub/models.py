
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class Audience(models.TextChoices):
    ALL = "ALL", "Everyone"
    RESIDENT = "RESIDENT", "Residents"
    SECURITY = "SECURITY", "Security"
    MANAGEMENT = "MANAGEMENT", "Management"


class Notice(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.ALL,
    )
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="community_notices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CommunityEvent(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    venue = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.ALL,
    )
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="community_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]

    def clean(self):
        errors = {}

        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors["ends_at"] = "The event end must be after its start."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title

class Delivery(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received at Gate"
        NOTIFIED = "NOTIFIED", "Resident Notified"
        COLLECTED = "COLLECTED", "Collected"
        RETURNED = "RETURNED", "Returned to Sender"

    resident = models.ForeignKey(
        "residents.ResidentProfile",
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    sender_name = models.CharField(max_length=150)
    tracking_number = models.CharField(max_length=100, blank=True)
    description = models.CharField(
        max_length=250,
        help_text="For example, grocery package, courier parcel or document.",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    notes = models.TextField(blank=True)

    received_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)

    received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="deliveries_received",
    )
    collected_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries_collected",
    )

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.sender_name} - {self.resident.user.username}"

    @property
    def is_pending_collection(self):
        return self.status in {
            self.Status.RECEIVED,
            self.Status.NOTIFIED,
        }

class IncidentReport(models.Model):
    class Category(models.TextChoices):
        SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY", "Suspicious Activity"
        THEFT = "THEFT", "Theft"
        PROPERTY_DAMAGE = "PROPERTY_DAMAGE", "Property Damage"
        FIRE = "FIRE", "Fire or Smoke"
        MEDICAL = "MEDICAL", "Medical Emergency"
        NOISE = "NOISE", "Noise Complaint"
        SAFETY = "SAFETY", "General Safety Concern"
        OTHER = "OTHER", "Other"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        REPORTED = "REPORTED", "Reported"
        INVESTIGATING = "INVESTIGATING", "Under Investigation"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices)
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    location = models.CharField(max_length=200)
    description = models.TextField()

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.REPORTED,
    )

    reported_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_incidents",
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_incidents",
        limit_choices_to={"role__in": ["SECURITY", "MANAGEMENT"]},
    )

    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.get_severity_display()}"


class GateEntry(models.Model):
    class EntryType(models.TextChoices):
        VEHICLE = "VEHICLE", "Vehicle"
        VISITOR = "VISITOR", "Visitor"
        SERVICE_PERSON = "SERVICE_PERSON", "Service Personnel"

    class Status(models.TextChoices):
        INSIDE = "INSIDE", "Currently Inside"
        EXITED = "EXITED", "Exited"

    entry_type = models.CharField(
        max_length=20,
        choices=EntryType.choices,
    )
    person_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, blank=True)

    vehicle_number = models.CharField(max_length=30, blank=True)
    vehicle_type = models.CharField(max_length=80, blank=True)

    organization = models.CharField(
        max_length=150,
        blank=True,
        help_text="Company or service provider, if applicable.",
    )
    purpose = models.CharField(max_length=250)

    resident = models.ForeignKey(
        "residents.ResidentProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_entries",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.INSIDE,
    )

    entry_time = models.DateTimeField(auto_now_add=True)
    exit_time = models.DateTimeField(null=True, blank=True)

    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="gate_entries_recorded",
    )
    exit_recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_exits_recorded",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-entry_time"]
        verbose_name = "Gate Entry"
        verbose_name_plural = "Gate Entries"

    def __str__(self):
        return f"{self.person_name} - {self.get_entry_type_display()}"

    def save(self, *args, **kwargs):
        if self.status == self.Status.EXITED and self.exit_time is None:
            self.exit_time = timezone.now()

        if self.status == self.Status.INSIDE:
            self.exit_time = None
            self.exit_recorded_by = None

        super().save(*args, **kwargs)

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Sum


class MaintenanceCharge(models.Model):
    apartment = models.ForeignKey(
        "residents.Apartment",
        on_delete=models.PROTECT,
        related_name="maintenance_charges",
    )
    billing_month = models.DateField(
        help_text="Use the first day of the billing month, e.g. 1 October 2026.",
    )
    description = models.CharField(
        max_length=200,
        default="Monthly Maintenance",
    )
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    due_date = models.DateField()
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="maintenance_charges_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-billing_month", "apartment"]
        constraints = [
            models.UniqueConstraint(
                fields=["apartment", "billing_month"],
                name="unique_apartment_maintenance_month",
            ),
        ]

    def __str__(self):
        return f"{self.apartment} - {self.billing_month:%B %Y}"

    @property
    def total_paid(self):
        result = self.payments.aggregate(total=Sum("amount"))
        return result["total"] or Decimal("0.00")

    @property
    def balance_due(self):
        return max(Decimal("0.00"), self.amount_due - self.total_paid)

    @property
    def payment_status(self):
        if self.total_paid >= self.amount_due:
            return "PAID"
        if self.total_paid > Decimal("0.00"):
            return "PARTIAL"
        return "PENDING"


class MaintenancePayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        UPI = "UPI", "UPI"
        CHEQUE = "CHEQUE", "Cheque"
        OTHER = "OTHER", "Other"

    charge = models.ForeignKey(
        MaintenanceCharge,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="maintenance_payments_recorded",
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"Payment ₹{self.amount} - {self.charge}"

    def clean(self):
        super().clean()
        errors = {}

        if self.amount is not None and self.amount <= Decimal("0.00"):
            errors["amount"] = "Payment amount must be greater than zero."

        if self.charge_id and self.amount is not None and self.amount > 0:
            other_payments = self.charge.payments.all()

            if self.pk:
                other_payments = other_payments.exclude(pk=self.pk)

            already_paid = (
                other_payments.aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            remaining = self.charge.amount_due - already_paid

            if self.amount > remaining:
                errors["amount"] = (
                    f"Payment exceeds the remaining balance of ₹{remaining:.2f}."
                )

        if errors:
            raise ValidationError(errors)

class AppNotification(models.Model):
    class Category(models.TextChoices):
        GENERAL = "GENERAL", "General"
        NOTICE = "NOTICE", "Notice"
        EVENT = "EVENT", "Community Event"
        DELIVERY = "DELIVERY", "Delivery"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        PAYMENT = "PAYMENT", "Maintenance Payment"
        INCIDENT = "INCIDENT", "Incident"

    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="app_notifications",
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    target_url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.recipient}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])