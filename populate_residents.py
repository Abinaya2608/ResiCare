
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from residents.models import Apartment, ResidentProfile

User = get_user_model()

created_apartments = 0
created_profiles = 0
skipped_profiles = 0

try:
    with transaction.atomic():
        for i in range(1, 16):
            username = f"resident{i:02d}"

            # Find the existing test user
            user = User.objects.get(username=username)

            # Do not change an existing resident profile
            if ResidentProfile.objects.filter(user=user).exists():
                print(f"Skipped existing profile: {username}")
                skipped_profiles += 1
                continue

            # Block A: apartments 102–108
            # Block B: apartments 201–208
            if i <= 7:
                building = "Block A"
                unit_number = str(101 + i)
                floor_number = 1
            else:
                building = "Block B"
                unit_number = str(194 + i)
                floor_number = 2

            apartment = Apartment.objects.filter(
                building_name=building,
                unit_number=unit_number
            ).first()

            if apartment is None:
                apartment = Apartment.objects.create(
                    building_name=building,
                    unit_number=unit_number,
                    floor_number=floor_number,
                    bedrooms=2,
                    monthly_maintenance=1500,
                    is_active=True,
                )
                created_apartments += 1
                print(f"Created apartment: {building} - {unit_number}")
            else:
                # Never assign a new resident to an occupied apartment
                if apartment.resident_profiles.exists():
                    raise ValueError(
                        f"{building} - {unit_number} already has "
                        "resident profiles. No changes were committed."
                    )

            ResidentProfile.objects.create(
                user=user,
                apartment=apartment,
                resident_type="OWNER",
            )

            created_profiles += 1
            print(
                f"Created profile: {username} -> "
                f"{building} - {unit_number}"
            )

    print("\n--- SUMMARY ---")
    print("New apartments:", created_apartments)
    print("New resident profiles:", created_profiles)
    print("Skipped existing profiles:", skipped_profiles)
    print("Total apartments:", Apartment.objects.count())
    print("Total resident profiles:", ResidentProfile.objects.count())
    print(
        "Residents without profiles:",
        User.objects.filter(role="RESIDENT")
        .exclude(resident_profile__isnull=False)
        .count()
    )

except Exception as error:
    print("\nOperation cancelled. Changes in this run were rolled back.")
    print("Reason:", error)
