
from django import forms

from .models import Notice, CommunityEvent, Delivery
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import MaintenanceCharge, MaintenancePayment

class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class NoticeForm(StyledModelForm):
    class Meta:
        model = Notice
        fields = ["title", "content", "audience", "is_published"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
        }


class CommunityEventForm(StyledModelForm):
    class Meta:
        model = CommunityEvent
        fields = [
            "title",
            "description",
            "venue",
            "starts_at",
            "ends_at",
            "audience",
            "is_published",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "starts_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        date_format = "%Y-%m-%dT%H:%M"
        self.fields["starts_at"].input_formats = [date_format]
        self.fields["ends_at"].input_formats = [date_format]

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("starts_at")
        end = cleaned_data.get("ends_at")

        if start and end and end <= start:
            self.add_error("ends_at", "The event end must be after its start.")

        return cleaned_data


class DeliveryForm(StyledModelForm):
    class Meta:
        model = Delivery
        fields = [
            "resident",
            "sender_name",
            "tracking_number",
            "description",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional delivery notes",
            }),
            "description": forms.TextInput(attrs={
                "placeholder": "e.g. Courier parcel",
            }),
            "tracking_number": forms.TextInput(attrs={
                "placeholder": "Optional tracking number",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resident"].queryset = (
            self.fields["resident"].queryset
            .select_related("user", "apartment")
            .filter(user__is_active=True)
        )
        self.fields["resident"].label_from_instance = (
            lambda profile: (
                f"{profile.user.get_full_name() or profile.user.username}"
                f" — {profile.apartment}"
                if profile.apartment
                else f"{profile.user.get_full_name() or profile.user.username}"
            )
        )

from django.contrib.auth import get_user_model
from .models import IncidentReport

User = get_user_model()


class IncidentReportForm(StyledModelForm):
    class Meta:
        model = IncidentReport
        fields = [
            "title",
            "category",
            "severity",
            "location",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Describe what happened, when, and any relevant details.",
            }),
            "location": forms.TextInput(attrs={
                "placeholder": "e.g. Block A entrance, parking area",
            }),
        }


class IncidentUpdateForm(StyledModelForm):
    class Meta:
        model = IncidentReport
        fields = [
            "status",
            "assigned_to",
            "resolution_notes",
        ]
        widgets = {
            "resolution_notes": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Investigation findings and resolution details",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            role__in=["SECURITY", "MANAGEMENT"],
            is_active=True,
        ).order_by("first_name", "username")
        self.fields["assigned_to"].required = False


from .models import GateEntry


class GateEntryForm(StyledModelForm):
    class Meta:
        model = GateEntry
        fields = [
            "entry_type",
            "person_name",
            "phone_number",
            "vehicle_number",
            "vehicle_type",
            "organization",
            "purpose",
            "resident",
            "notes",
        ]
        widgets = {
            "purpose": forms.TextInput(attrs={
                "placeholder": "e.g. Parcel delivery, plumbing repair, family visit",
            }),
            "vehicle_number": forms.TextInput(attrs={
                "placeholder": "e.g. TN 38 AB 1234",
            }),
            "notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Additional details, if any",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resident"].required = False
        self.fields["resident"].queryset = (
            self.fields["resident"].queryset
            .select_related("user", "apartment")
            .filter(user__is_active=True)
        )
        self.fields["resident"].label_from_instance = (
            lambda profile: (
                f"{profile.user.get_full_name() or profile.user.username}"
                f" — {profile.apartment}"
                if profile.apartment
                else f"{profile.user.get_full_name() or profile.user.username}"
            )
        )

    def clean(self):
        cleaned_data = super().clean()

        entry_type = cleaned_data.get("entry_type")
        vehicle_number = cleaned_data.get("vehicle_number", "").strip()

        if entry_type == GateEntry.EntryType.VEHICLE and not vehicle_number:
            self.add_error(
                "vehicle_number",
                "Enter the vehicle registration number for a vehicle entry.",
            )

        return cleaned_data

class MaintenanceChargeForm(StyledModelForm):
    class Meta:
        model = MaintenanceCharge
        fields = [
            "apartment",
            "billing_month",
            "description",
            "amount_due",
            "due_date",
            "notes",
        ]
        widgets = {
            "billing_month": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "amount_due": forms.NumberInput(attrs={
                "min": "0.01",
                "step": "0.01",
                "placeholder": "e.g. 1500.00",
            }),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_billing_month(self):
        month = self.cleaned_data["billing_month"]

        if month.day != 1:
            raise ValidationError(
                "Select the first day of the billing month."
            )

        return month

    def clean_amount_due(self):
        amount = self.cleaned_data["amount_due"]

        if amount <= Decimal("0.00"):
            raise ValidationError("The maintenance charge must be greater than zero.")

        return amount

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get("billing_month")
        due_date = cleaned_data.get("due_date")

        if month and due_date and due_date < month:
            self.add_error(
                "due_date",
                "The due date cannot be before the billing month begins.",
            )

        return cleaned_data


class MaintenancePaymentForm(StyledModelForm):
    class Meta:
        model = MaintenancePayment
        fields = [
            "amount",
            "payment_method",
            "reference_number",
            "notes",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Enter amount received",
            }),
            "notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional payment notes",
            }),
        }

    def __init__(self, *args, charge=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.charge = charge

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount <= Decimal("0.00"):
            raise ValidationError("Payment must be greater than zero.")

        if self.charge is not None and amount > self.charge.balance_due:
            raise ValidationError(
                f"The outstanding balance is ₹{self.charge.balance_due:.2f}."
            )

        return amount
