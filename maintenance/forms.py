
from django import forms
from django.contrib.auth import get_user_model

from .models import MaintenanceRequest

User = get_user_model()


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "title",
            "category",
            "description",
            "location",
            "priority",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Briefly describe the issue",
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Explain the problem clearly",
            }),
            "location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Flat number or common area",
            }),
            "priority": forms.Select(attrs={
                "class": "form-select",
            }),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if not title:
            raise forms.ValidationError(
                "Enter a complaint title."
            )

        return title

    def clean_description(self):
        description = self.cleaned_data["description"].strip()

        if len(description) < 10:
            raise forms.ValidationError(
                "Please provide at least 10 characters describing the issue."
            )

        return description



class MaintenanceUpdateForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "status",
            "assigned_to",
            "resolution_notes",
        ]
        widgets = {
            "status": forms.Select(attrs={
                "class": "form-select",
            }),
            "assigned_to": forms.Select(attrs={
                "class": "form-select",
            }),
            "resolution_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Work completed or next steps",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and self.user.role == "SECURITY":
            # Security staff cannot assign or reassign requests.
            self.fields.pop("assigned_to", None)

            # Restrict status choices to the permitted workflow.
            # Adjust these if your project uses different status rules.
            self.fields["status"].choices = [
                choice
                for choice in self.fields["status"].choices
                if choice[0] in [
                    MaintenanceRequest.Status.IN_PROGRESS,
                    MaintenanceRequest.Status.ON_HOLD,
                    MaintenanceRequest.Status.RESOLVED,
                ]
            ]

        else:
            self.fields["assigned_to"].required = False
            self.fields["assigned_to"].queryset = User.objects.filter(
                role="SECURITY",
                is_active=True,
            ).order_by("username")
            self.fields["assigned_to"].label = "Assign to security staff"
