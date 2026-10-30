
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from residents.models import Apartment, ResidentProfile
from .forms import FacilityBookingForm
from .models import Facility, FacilityBooking


User = get_user_model()


class FacilityModelTests(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name="Community Hall",
            description="Hall for resident events",
            location="Block A",
            capacity=50,
            opening_time=time(9, 0),
            closing_time=time(18, 0),
        )

    def test_facility_string_representation(self):
        self.assertEqual(str(self.facility), "Community Hall")

    def test_facility_rejects_closing_time_before_opening_time(self):
        self.facility.closing_time = time(8, 0)

        with self.assertRaises(ValidationError):
            self.facility.full_clean()

    def test_facility_rejects_equal_opening_and_closing_times(self):
        self.facility.closing_time = self.facility.opening_time

        with self.assertRaises(ValidationError):
            self.facility.full_clean()


class FacilityBookingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="resident1",
            password="test-password",
            role="RESIDENT",
        )

        self.apartment = Apartment.objects.create(
            building_name="Block A",
            unit_number="101",
            floor_number=1,
            bedrooms=2,
            area_sqft=1000,
            monthly_maintenance=Decimal("1500.00"),
        )

        self.profile = ResidentProfile.objects.create(
            user=self.user,
            apartment=self.apartment,
            resident_type="OWNER",
        )

        self.facility = Facility.objects.create(
            name="Community Hall",
            description="Hall for resident events",
            location="Block A",
            capacity=50,
            opening_time=time(9, 0),
            closing_time=time(18, 0),
        )

        self.booking_date = timezone.localdate() + timedelta(days=1)

    def make_booking(self, **overrides):
        data = {
            "facility": self.facility,
            "resident": self.profile,
            "booking_date": self.booking_date,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "purpose": "Community meeting",
            "status": FacilityBooking.Status.PENDING,
        }
        data.update(overrides)
        return FacilityBooking(**data)

    def test_booking_rejects_end_time_before_start_time(self):
        booking = self.make_booking(
            start_time=time(12, 0),
            end_time=time(11, 0),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_rejects_past_date(self):
        booking = self.make_booking(
            booking_date=timezone.localdate() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_rejects_inactive_facility(self):
        self.facility.is_active = False
        self.facility.save()

        booking = self.make_booking()

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_rejects_time_outside_operating_hours(self):
        booking = self.make_booking(
            start_time=time(8, 0),
            end_time=time(10, 0),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_approved_booking_rejects_overlapping_approved_booking(self):
        existing = self.make_booking(
            status=FacilityBooking.Status.APPROVED,
        )
        existing.full_clean()
        existing.save()

        overlapping = self.make_booking(
            start_time=time(10, 30),
            end_time=time(11, 30),
            status=FacilityBooking.Status.APPROVED,
        )

        with self.assertRaises(ValidationError):
            overlapping.full_clean()

    def test_approved_booking_allows_non_overlapping_time(self):
        existing = self.make_booking(
            status=FacilityBooking.Status.APPROVED,
        )
        existing.full_clean()
        existing.save()

        another = self.make_booking(
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=FacilityBooking.Status.APPROVED,
        )

        another.full_clean()

    def test_pending_booking_does_not_trigger_approved_booking_conflict(self):
        existing = self.make_booking(
            status=FacilityBooking.Status.APPROVED,
        )
        existing.full_clean()
        existing.save()

        pending = self.make_booking(
            start_time=time(10, 30),
            end_time=time(11, 30),
            status=FacilityBooking.Status.PENDING,
        )

        pending.full_clean()


class FacilityBookingFormTests(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name="Community Hall",
            description="Hall for resident events",
            location="Block A",
            capacity=50,
            opening_time=time(9, 0),
            closing_time=time(18, 0),
        )

    def valid_form_data(self):
        return {
            "facility": self.facility.pk,
            "booking_date": (
                timezone.localdate() + timedelta(days=1)
            ).isoformat(),
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Community meeting",
        }

    def test_valid_booking_form(self):
        form = FacilityBookingForm(data=self.valid_form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_inactive_facility_is_not_available_in_form(self):
        self.facility.is_active = False
        self.facility.save()

        form = FacilityBookingForm(data=self.valid_form_data())

        self.assertFalse(form.is_valid())
        self.assertIn("facility", form.errors)

    def test_form_rejects_whitespace_only_purpose(self):
        data = self.valid_form_data()
        data["purpose"] = "   "

        form = FacilityBookingForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("purpose", form.errors)

    def test_form_rejects_past_booking_date(self):
        data = self.valid_form_data()
        data["booking_date"] = (
            timezone.localdate() - timedelta(days=1)
        ).isoformat()

        form = FacilityBookingForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("booking_date", form.errors)

    def test_form_rejects_end_time_before_start_time(self):
        data = self.valid_form_data()
        data["start_time"] = "12:00"
        data["end_time"] = "11:00"

        form = FacilityBookingForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)

    
from django.urls import reverse


class FacilityBookingViewTests(TestCase):
    def setUp(self):
        self.resident_user = User.objects.create_user(
            username="resident_view",
            password="test-password",
            role="RESIDENT",
        )
        self.other_resident_user = User.objects.create_user(
            username="resident_other",
            password="test-password",
            role="RESIDENT",
        )
        self.management_user = User.objects.create_user(
            username="manager_view",
            password="test-password",
            role="MANAGEMENT",
        )
        self.security_user = User.objects.create_user(
            username="security_view",
            password="test-password",
            role="SECURITY",
        )

        self.apartment = Apartment.objects.create(
            building_name="Block B",
            unit_number="201",
            floor_number=2,
            bedrooms=2,
            area_sqft=1000,
            monthly_maintenance=Decimal("1500.00"),
        )
        self.other_apartment = Apartment.objects.create(
            building_name="Block B",
            unit_number="202",
            floor_number=2,
            bedrooms=2,
            area_sqft=1000,
            monthly_maintenance=Decimal("1500.00"),
        )

        self.profile = ResidentProfile.objects.create(
            user=self.resident_user,
            apartment=self.apartment,
            resident_type="OWNER",
        )
        self.other_profile = ResidentProfile.objects.create(
            user=self.other_resident_user,
            apartment=self.other_apartment,
            resident_type="OWNER",
        )

        self.facility = Facility.objects.create(
            name="Swimming Pool",
            description="Community swimming pool",
            location="Block B",
            capacity=20,
            opening_time=time(6, 0),
            closing_time=time(20, 0),
        )

        self.booking = FacilityBooking.objects.create(
            facility=self.facility,
            resident=self.profile,
            booking_date=timezone.localdate() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose="Swimming practice",
            status=FacilityBooking.Status.PENDING,
        )

        self.client.force_login(self.resident_user)

    def test_resident_dashboard_shows_only_own_bookings(self):
        FacilityBooking.objects.create(
            facility=self.facility,
            resident=self.other_profile,
            booking_date=timezone.localdate() + timedelta(days=2),
            start_time=time(11, 0),
            end_time=time(12, 0),
            purpose="Family swimming",
        )

        response = self.client.get(reverse("facilities:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Swimming practice")
        self.assertNotContains(response, "Family swimming")

    def test_resident_can_create_booking(self):
        response = self.client.post(
            reverse("facilities:create_booking"),
            {
                "facility": self.facility.pk,
                "booking_date": (
                    timezone.localdate() + timedelta(days=2)
                ).isoformat(),
                "start_time": "12:00",
                "end_time": "13:00",
                "purpose": "Yoga practice",
            },
        )

        self.assertRedirects(
            response,
            reverse("facilities:dashboard"),
        )
        self.assertTrue(
            FacilityBooking.objects.filter(
                resident=self.profile,
                purpose="Yoga practice",
                status=FacilityBooking.Status.PENDING,
            ).exists()
        )

    def test_resident_cannot_open_another_residents_booking(self):
        self.client.force_login(self.other_resident_user)

        response = self.client.get(
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_security_cannot_open_pending_booking(self):
        self.client.force_login(self.security_user)

        response = self.client.get(
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_management_can_approve_pending_booking(self):
        self.client.force_login(self.management_user)

        response = self.client.post(
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            ),
            {
                "action": "approve",
                "management_notes": "Approved for use.",
            },
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            FacilityBooking.Status.APPROVED,
        )
        self.assertEqual(self.booking.reviewed_by, self.management_user)
        self.assertIsNotNone(self.booking.reviewed_at)
        self.assertRedirects(
            response,
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            ),
        )

    def test_management_can_reject_pending_booking(self):
        self.client.force_login(self.management_user)

        response = self.client.post(
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            ),
            {
                "action": "reject",
                "management_notes": "Please choose another date.",
            },
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            FacilityBooking.Status.REJECTED,
        )
        self.assertEqual(
            self.booking.management_notes,
            "Please choose another date.",
        )
        self.assertEqual(self.booking.reviewed_by, self.management_user)

    def test_resident_can_cancel_pending_booking(self):
        response = self.client.post(
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            ),
            {"action": "cancel"},
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            FacilityBooking.Status.CANCELLED,
        )
        self.assertRedirects(
            response,
            reverse("facilities:dashboard"),
        )

    def test_resident_cannot_cancel_approved_booking(self):
        self.booking.status = FacilityBooking.Status.APPROVED
        self.booking.save()

        self.client.post(
            reverse(
                "facilities:booking_detail",
                kwargs={"booking_id": self.booking.pk},
            ),
            {"action": "cancel"},
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            FacilityBooking.Status.APPROVED,
        )
