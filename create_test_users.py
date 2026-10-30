
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

created = 0
skipped = 0

# Create 15 resident accounts
for i in range(1, 16):
    username = f"resident{i:02d}"

    if User.objects.filter(username=username).exists():
        print(f"Skipped existing user: {username}")
        skipped += 1
        continue

    User.objects.create_user(
        username=username,
        password=f"Resident@{i:02d}X",
        first_name=f"Resident{i}",
        last_name="ResiCare",
        email=f"resident{i:02d}@example.com",
        role="RESIDENT",
        phone_number=str(9000000000 + i),
    )
    print(f"Created resident: {username}")
    created += 1

# Create 5 security accounts
for i in range(1, 6):
    username = f"security{i:02d}"

    if User.objects.filter(username=username).exists():
        print(f"Skipped existing user: {username}")
        skipped += 1
        continue

    User.objects.create_user(
        username=username,
        password=f"Security@{i:02d}X",
        first_name=f"Security{i}",
        last_name="ResiCare",
        email=f"security{i:02d}@example.com",
        role="SECURITY",
        phone_number=str(9100000000 + i),
    )
    print(f"Created security: {username}")
    created += 1

print("\n--- SUMMARY ---")
print("Created:", created)
print("Skipped:", skipped)
print("Total users:", User.objects.count())
print("Residents:", User.objects.filter(role="RESIDENT").count())
print("Security:", User.objects.filter(role="SECURITY").count())
print("Management:", User.objects.filter(role="MANAGEMENT").count())
