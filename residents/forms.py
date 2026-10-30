
from django import forms

from .models import ResidentProfile


class ResidentProfileForm(forms.ModelForm):
    class Meta:
        model = ResidentProfile
        fields = (
            "move_in_date",
            "emergency_contact_name",
            "emergency_contact_phone",
        )

        widgets = {
            "move_in_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "emergency_contact_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter emergency contact name",
                    "maxlength": 100,
                }
            ),
            "emergency_contact_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter emergency contact phone number",
                    "maxlength": 15,
                    "autocomplete": "tel",
                }
            ),
        }

    def clean_emergency_contact_phone(self):
        phone = self.cleaned_data.get("emergency_contact_phone", "").strip()

        if phone and not all(
            character.isdigit() or character in "+-() "
            for character in phone
        ):
            raise forms.ValidationError(
                "Enter a valid phone number using digits and optional +, -, "
                "parentheses, or spaces."
            )

        digits = "".join(character for character in phone if character.isdigit())

        if phone and not 7 <= len(digits) <= 15:
            raise forms.ValidationError(
                "The phone number must contain between 7 and 15 digits."
            )

        return phone

    def clean_emergency_contact_name(self):
        name = self.cleaned_data.get("emergency_contact_name", "").strip()
        phone = self.data.get("emergency_contact_phone", "").strip()

        if phone and not name:
            raise forms.ValidationError(
                "Enter the emergency contact's name when providing a phone number."
            )

        return name
