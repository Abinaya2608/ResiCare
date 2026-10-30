
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Apartment(models.Model):
    building_name = models.CharField(max_length=100, default="Main Building")
    unit_number = models.CharField(max_length=20)
    floor_number = models.PositiveIntegerField(default=0)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    area_sqft = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    monthly_maintenance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["building_name", "unit_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["building_name", "unit_number"],
                name="unique_apartment_unit_per_building",
            )
        ]

    def __str__(self):
        return f"{self.building_name} - {self.unit_number}"

    @property
    def occupied(self):
        return self.resident_profiles.filter(
            user__is_active=True
        ).exists()


class ResidentProfile(models.Model):
    class ResidentType(models.TextChoices):
        OWNER = "OWNER", "Owner"
        TENANT = "TENANT", "Tenant"
        FAMILY_MEMBER = "FAMILY_MEMBER", "Family Member"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resident_profile",
    )
    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.PROTECT,
        related_name="resident_profiles",
        null=True,
        blank=True,
    )
    resident_type = models.CharField(
        max_length=20,
        choices=ResidentType.choices,
        default=ResidentType.OWNER,
    )
    move_in_date = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"{self.user.username} - {self.get_resident_type_display()}"
