
from django import forms
from django.utils import timezone

from .models import VisitorInvitation, VisitorLog


class VisitorInvitationForm(forms.ModelForm):
    class Meta:
        model = VisitorInvitation
        fields = (
            "visitor_name",
            "visitor_phone",
            "purpose",
            "expected_at",
        )

        widgets = {
            "visitor_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter visitor's full name",
                "maxlength": 100,
            }),
            "visitor_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter visitor's phone number",
                "maxlength": 15,
                "autocomplete": "tel",
            }),
            "purpose": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Family visit, delivery, maintenance",
                "maxlength": 250,
            }),
            "expected_at": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
        }

    def clean_visitor_name(self):
        name = self.cleaned_data["visitor_name"].strip()

        if not name:
            raise forms.ValidationError("Enter the visitor's name.")

        return name

    def clean_visitor_phone(self):
        phone = self.cleaned_data["visitor_phone"].strip()

        if not all(char.isdigit() or char in "+-() " for char in phone):
            raise forms.ValidationError(
                "Use digits and optional +, -, parentheses or spaces."
            )

        digits = "".join(char for char in phone if char.isdigit())

        if not 7 <= len(digits) <= 15:
            raise forms.ValidationError(
                "The phone number must contain 7 to 15 digits."
            )

        return phone

    def clean_expected_at(self):
        expected_at = self.cleaned_data["expected_at"]

        if expected_at <= timezone.now():
            raise forms.ValidationError(
                "Choose a future date and time for the visit."
            )

        return expected_at


class WalkInVisitorForm(forms.ModelForm):
    class Meta:
        model = VisitorLog
        fields = (
            "resident",
            "visitor_name",
            "visitor_phone",
            "purpose",
            "notes",
        )

        widgets = {
            "resident": forms.Select(attrs={
                "class": "form-select",
            }),
            "visitor_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Visitor's full name",
            }),
            "visitor_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Visitor's phone number",
            }),
            "purpose": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Purpose of visit",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional notes",
            }),
        }

    def clean_visitor_phone(self):
        phone = self.cleaned_data["visitor_phone"].strip()

        if not all(char.isdigit() or char in "+-() " for char in phone):
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        digits = "".join(char for char in phone if char.isdigit())

        if not 7 <= len(digits) <= 15:
            raise forms.ValidationError(
                "The phone number must contain 7 to 15 digits."
            )

        return phone
