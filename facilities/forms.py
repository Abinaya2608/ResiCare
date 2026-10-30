
from django import forms
from django.utils import timezone

from .models import Facility, FacilityBooking


class FacilityBookingForm(forms.ModelForm):
    class Meta:
        model = FacilityBooking
        fields = [
            "facility",
            "booking_date",
            "start_time",
            "end_time",
            "purpose",
        ]
        widgets = {
            "facility": forms.Select(attrs={
                "class": "form-select",
            }),
            "booking_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "start_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "end_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "purpose": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Describe the purpose of your booking",
                "maxlength": 250,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["facility"].queryset = Facility.objects.filter(
            is_active=True
        ).order_by("name")

    def clean_purpose(self):
        purpose = self.cleaned_data["purpose"].strip()

        if not purpose:
            raise forms.ValidationError(
                "Please describe the purpose of your booking."
            )

        return purpose

    def clean(self):
        cleaned_data = super().clean()

        facility = cleaned_data.get("facility")
        booking_date = cleaned_data.get("booking_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if booking_date and booking_date < timezone.localdate():
            self.add_error(
                "booking_date",
                "Choose today or a future date.",
            )

        if start_time and end_time and end_time <= start_time:
            self.add_error(
                "end_time",
                "End time must be later than start time.",
            )

        if facility and start_time and end_time:
            if (
                start_time < facility.opening_time
                or end_time > facility.closing_time
            ):
                self.add_error(
                    "start_time",
                    f"Available hours are "
                    f"{facility.opening_time.strftime('%H:%M')} to "
                    f"{facility.closing_time.strftime('%H:%M')}.",
                )

        return cleaned_data


class FacilityBookingReviewForm(forms.ModelForm):
    class Meta:
        model = FacilityBooking
        fields = ["management_notes"]
        widgets = {
            "management_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional decision notes",
            }),
        }
