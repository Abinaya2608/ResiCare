
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from .forms import ResidentProfileForm
from .models import Apartment, ResidentProfile

User = get_user_model()


class ApartmentModelTests(TestCase):
    def setUp(self):
        self.apartment = Apartment.objects.create(
            building_name="Main Building",
            unit_number="A101",
            floor_number=1,
            bedrooms=2,
            area_sqft=1000,
            monthly_maintenance=Decimal("1500.00"),
        )

    def test_apartment_creation(self):
        self.assertEqual(self.apartment.unit_number, "A101")
        self.assertEqual(self.apartment.monthly_maintenance, Decimal("1500.00"))

    def test_apartment_string_representation(self):
        self.assertEqual(str(self.apartment), "Main Building - A101")

    def test_duplicate_unit_in_same_building_is_rejected(self):
        with self.assertRaises(IntegrityError):
         with transaction.atomic():
            Apartment.objects.create(
                building_name="Main Building",
                unit_number="A101",
            )
            
    def test_same_unit_number_in_different_building_is_allowed(self):
        apartment = Apartment.objects.create(
            building_name="Annex",
            unit_number="A101",
        )
        self.assertEqual(apartment.building_name, "Annex")

    def test_area_must_be_positive_when_provided(self):
        apartment = Apartment(
            building_name="Main Building",
            unit_number="A102",
            area_sqft=0,
        )
        with self.assertRaises(ValidationError):
            apartment.full_clean()

    def test_apartment_starts_unoccupied(self):
        self.assertFalse(self.apartment.occupied)

    def test_apartment_is_occupied_by_active_resident(self):
        user = User.objects.create_user(
            username="resident1",
            password="TestPass123!",
            is_active=True,
        )
        ResidentProfile.objects.create(user=user, apartment=self.apartment)

        self.assertTrue(self.apartment.occupied)

    def test_inactive_user_does_not_occupy_apartment(self):
        user = User.objects.create_user(
            username="inactive1",
            password="TestPass123!",
            is_active=False,
        )
        ResidentProfile.objects.create(user=user, apartment=self.apartment)

        self.assertFalse(self.apartment.occupied)

    def test_apartment_cannot_be_deleted_while_profile_references_it(self):
        user = User.objects.create_user(
            username="resident2",
            password="TestPass123!",
        )
        ResidentProfile.objects.create(
            user=user,
            apartment=self.apartment,
        )

        with self.assertRaises(ProtectedError):
            self.apartment.delete()

class ResidentProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="abi_test",
            password="TestPass123!",
        )

    def test_profile_creation(self):
        profile = ResidentProfile.objects.create(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertIsNone(profile.apartment)
        self.assertEqual(
            profile.resident_type,
            ResidentProfile.ResidentType.OWNER,
        )

    def test_profile_string_representation(self):
        profile = ResidentProfile.objects.create(user=self.user)
        self.assertEqual(str(profile), "abi_test - Owner")

    def test_user_can_have_only_one_resident_profile(self):
        ResidentProfile.objects.create(user=self.user)

        with self.assertRaises(ValidationError):
            ResidentProfile(user=self.user).validate_unique()

    def test_profile_requires_valid_resident_type(self):
        profile = ResidentProfile(
            user=self.user,
            resident_type="INVALID",
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()


class ResidentProfileFormTests(TestCase):
    def valid_form_data(self):
        return {
            "move_in_date": date.today().isoformat(),
            "emergency_contact_name": "Emergency Contact",
            "emergency_contact_phone": "9876543210",
        }

    def test_valid_form(self):
        form = ResidentProfileForm(data=self.valid_form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_phone_is_optional(self):
        form = ResidentProfileForm(
            data={
                "move_in_date": "",
                "emergency_contact_name": "",
                "emergency_contact_phone": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_phone_with_letters_is_rejected(self):
        data = self.valid_form_data()
        data["emergency_contact_phone"] = "98765ABCDE"
        form = ResidentProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("emergency_contact_phone", form.errors)

    def test_phone_with_fewer_than_seven_digits_is_rejected(self):
        data = self.valid_form_data()
        data["emergency_contact_phone"] = "123456"
        form = ResidentProfileForm(data=data)
        self.assertFalse(form.is_valid())

    def test_phone_with_more_than_fifteen_digits_is_rejected(self):
        data = self.valid_form_data()
        data["emergency_contact_phone"] = "1234567890123456"
        form = ResidentProfileForm(data=data)
        self.assertFalse(form.is_valid())

    def test_phone_requires_contact_name(self):
        data = self.valid_form_data()
        data["emergency_contact_name"] = ""
        form = ResidentProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("emergency_contact_name", form.errors)

    def test_contact_name_and_phone_are_trimmed(self):
        data = self.valid_form_data()
        data["emergency_contact_name"] = "  Contact Name  "
        data["emergency_contact_phone"] = " 9876543210 "
        form = ResidentProfileForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["emergency_contact_name"],
            "Contact Name",
        )
        self.assertEqual(
            form.cleaned_data["emergency_contact_phone"],
            "9876543210",
        )


class ResidentProfileViewTests(TestCase):
    def setUp(self):
        self.apartment = Apartment.objects.create(
            building_name="Main Building",
            unit_number="B101",
        )
        self.resident_user = User.objects.create_user(
            username="resident_view",
            password="TestPass123!",
            role=User.Role.RESIDENT,
        )
        self.profile = ResidentProfile.objects.create(
            user=self.resident_user,
            apartment=self.apartment,
            resident_type=ResidentProfile.ResidentType.TENANT,
        )
        self.url = reverse("residents:my_profile")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/?next="))

    def test_resident_can_view_own_profile(self):
        self.client.login(username="resident_view", password="TestPass123!")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["profile"], self.profile)

    def test_non_resident_cannot_access_profile(self):
        management_user = User.objects.create_user(
            username="manager_view",
            password="TestPass123!",
            role=User.Role.MANAGEMENT,
        )
        self.client.force_login(management_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_missing_profile_redirects_to_dashboard(self):
        user = User.objects.create_user(
            username="resident_missing",
            password="TestPass123!",
            role=User.Role.RESIDENT,
        )
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_resident_can_update_emergency_contact(self):
        self.client.force_login(self.resident_user)

        response = self.client.post(
            self.url,
            {
                "move_in_date": "",
                "emergency_contact_name": "Updated Contact",
                "emergency_contact_phone": "9876543210",
            },
        )

        self.assertRedirects(response, self.url)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.emergency_contact_name,
            "Updated Contact",
        )
        self.assertEqual(
            self.profile.emergency_contact_phone,
            "9876543210",
        )

    def test_invalid_form_does_not_update_profile(self):
        self.client.force_login(self.resident_user)

        response = self.client.post(
            self.url,
            {
                "move_in_date": "",
                "emergency_contact_name": "",
                "emergency_contact_phone": "123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.emergency_contact_phone, "")

    def test_post_cannot_change_apartment_or_resident_type(self):
        self.client.force_login(self.resident_user)

        other_apartment = Apartment.objects.create(
            building_name="Annex",
            unit_number="B202",
        )

        response = self.client.post(
            self.url,
            {
                "move_in_date": "",
                "emergency_contact_name": "Contact",
                "emergency_contact_phone": "9876543210",
                "apartment": str(other_apartment.pk),
                "resident_type": ResidentProfile.ResidentType.OWNER,
            },
        )

        self.assertRedirects(response, self.url)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.apartment, self.apartment)
        self.assertEqual(
            self.profile.resident_type,
            ResidentProfile.ResidentType.TENANT,
        )
