
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from residents.models import Apartment, ResidentProfile
from .forms import (
    CommunityEventForm,
    GateEntryForm,
    MaintenanceChargeForm,
    MaintenancePaymentForm,
)
from .models import (
    AppNotification,
    CommunityEvent,
    Delivery,
    GateEntry,
    MaintenanceCharge,
    MaintenancePayment,
    Notice,
)

User = get_user_model()


class CommunityModelTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.management = User.objects.create_user(
            username="management_test",
            password="TestPass123!",
            role="MANAGEMENT",
        )
        cls.security = User.objects.create_user(
            username="security_test",
            password="TestPass123!",
            role="SECURITY",
        )
        cls.resident_user = User.objects.create_user(
            username="resident_test",
            password="TestPass123!",
            role="RESIDENT",
        )
        cls.other_resident_user = User.objects.create_user(
            username="other_resident_test",
            password="TestPass123!",
            role="RESIDENT",
        )

        cls.apartment = Apartment.objects.create(
            building_name="Block A",
            unit_number="101",
            floor_number=1,
            bedrooms=2,
            area_sqft=1000,
            monthly_maintenance=Decimal("1500.00"),
        )
        cls.other_apartment = Apartment.objects.create(
            building_name="Block A",
            unit_number="102",
            floor_number=1,
            bedrooms=2,
            area_sqft=1000,
            monthly_maintenance=Decimal("1500.00"),
        )

        cls.resident = ResidentProfile.objects.create(
            user=cls.resident_user,
            apartment=cls.apartment,
        )
        cls.other_resident = ResidentProfile.objects.create(
            user=cls.other_resident_user,
            apartment=cls.other_apartment,
        )


class CommunityEventFormTests(CommunityModelTestBase):
    def event_data(self, starts_at, ends_at):
        return {
            "title": "Community Meeting",
            "description": "Monthly resident meeting",
            "venue": "Community Hall",
            "starts_at": starts_at.strftime("%Y-%m-%dT%H:%M"),
            "ends_at": ends_at.strftime("%Y-%m-%dT%H:%M"),
            "audience": "ALL",
            "is_published": True,
        }

    def test_event_form_accepts_valid_times(self):
        start = timezone.localtime() + timedelta(days=2)
        end = start + timedelta(hours=1)
        form = CommunityEventForm(data=self.event_data(start, end))

        self.assertTrue(form.is_valid(), form.errors)

    def test_event_form_rejects_end_before_start(self):
        start = timezone.localtime() + timedelta(days=2)
        end = start - timedelta(hours=1)
        form = CommunityEventForm(data=self.event_data(start, end))

        self.assertFalse(form.is_valid())
        self.assertIn("ends_at", form.errors)

    def test_event_form_rejects_equal_start_and_end(self):
        start = timezone.localtime() + timedelta(days=2)
        form = CommunityEventForm(data=self.event_data(start, start))

        self.assertFalse(form.is_valid())
        self.assertIn("ends_at", form.errors)


class GateEntryFormTests(CommunityModelTestBase):
    def gate_data(self, **overrides):
        data = {
            "entry_type": "VEHICLE",
            "person_name": "Delivery Driver",
            "phone_number": "9876543210",
            "vehicle_number": "TN 38 AB 1234",
            "vehicle_type": "Car",
            "organization": "Courier Service",
            "purpose": "Package delivery",
            "resident": str(self.resident.pk),
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_vehicle_entry_requires_vehicle_number(self):
        form = GateEntryForm(
            data=self.gate_data(vehicle_number="")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("vehicle_number", form.errors)

    def test_vehicle_entry_accepts_vehicle_number(self):
        form = GateEntryForm(data=self.gate_data())

        self.assertTrue(form.is_valid(), form.errors)


class MaintenanceChargeFormTests(CommunityModelTestBase):
    def charge_data(self, **overrides):
        data = {
            "apartment": str(self.apartment.pk),
            "billing_month": "2026-10-01",
            "description": "Monthly Maintenance",
            "amount_due": "1500.00",
            "due_date": "2026-10-10",
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_charge_form_accepts_valid_data(self):
        form = MaintenanceChargeForm(data=self.charge_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_charge_form_rejects_billing_month_not_first_day(self):
        form = MaintenanceChargeForm(
            data=self.charge_data(billing_month="2026-10-15")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("billing_month", form.errors)

    def test_charge_form_rejects_zero_amount(self):
        form = MaintenanceChargeForm(
            data=self.charge_data(amount_due="0.00")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("amount_due", form.errors)

    def test_charge_form_rejects_due_date_before_billing_month(self):
        form = MaintenanceChargeForm(
            data=self.charge_data(due_date="2026-09-30")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)


class MaintenancePaymentModelTests(CommunityModelTestBase):
    def setUp(self):
        self.charge = MaintenanceCharge.objects.create(
            apartment=self.apartment,
            billing_month=timezone.datetime(2026, 10, 1).date(),
            description="Monthly Maintenance",
            amount_due=Decimal("1500.00"),
            due_date=timezone.datetime(2026, 10, 10).date(),
            created_by=self.management,
        )

    def test_charge_starts_with_full_balance(self):
        self.assertEqual(self.charge.total_paid, Decimal("0.00"))
        self.assertEqual(self.charge.balance_due, Decimal("1500.00"))
        self.assertEqual(self.charge.payment_status, "PENDING")

    def test_partial_payment_updates_balance(self):
        payment = MaintenancePayment(
            charge=self.charge,
            amount=Decimal("500.00"),
            payment_method="UPI",
            received_by=self.management,
        )
        payment.full_clean()
        payment.save()

        self.assertEqual(self.charge.total_paid, Decimal("500.00"))
        self.assertEqual(self.charge.balance_due, Decimal("1000.00"))
        self.assertEqual(self.charge.payment_status, "PARTIAL")

    def test_payment_model_rejects_zero_amount(self):
        payment = MaintenancePayment(
            charge=self.charge,
            amount=Decimal("0.00"),
            payment_method="CASH",
            received_by=self.management,
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_model_rejects_overpayment(self):
        payment = MaintenancePayment(
            charge=self.charge,
            amount=Decimal("1500.01"),
            payment_method="UPI",
            received_by=self.management,
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_full_payment_marks_charge_paid(self):
        payment = MaintenancePayment(
            charge=self.charge,
            amount=Decimal("1500.00"),
            payment_method="BANK_TRANSFER",
            received_by=self.management,
        )
        payment.full_clean()
        payment.save()

        self.assertEqual(self.charge.balance_due, Decimal("0.00"))
        self.assertEqual(self.charge.payment_status, "PAID")


class CommunityAccessTests(CommunityModelTestBase):
    def test_resident_cannot_view_another_residents_charge(self):
        charge = MaintenanceCharge.objects.create(
            apartment=self.other_apartment,
            billing_month=timezone.datetime(2026, 10, 1).date(),
            amount_due=Decimal("1500.00"),
            due_date=timezone.datetime(2026, 10, 10).date(),
            created_by=self.management,
        )

        self.client.force_login(self.resident_user)

        response = self.client.get(
            "/community/maintenance-dues/"
            f"{charge.pk}/"
        )

        self.assertEqual(response.status_code, 403)

    def test_resident_sees_only_own_notifications(self):
        own_notification = AppNotification.objects.create(
            recipient=self.resident_user,
            title="Your parcel arrived",
            message="Please collect your parcel.",
            category="DELIVERY",
        )
        AppNotification.objects.create(
            recipient=self.other_resident_user,
            title="Private notice",
            message="This belongs to another resident.",
        )

        self.client.force_login(self.resident_user)
        response = self.client.get("/community/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_notification.title)
        self.assertNotContains(response, "Private notice")

    def test_resident_cannot_open_another_users_notification(self):
        notification = AppNotification.objects.create(
            recipient=self.other_resident_user,
            title="Private notification",
            message="Private content",
        )

        self.client.force_login(self.resident_user)
        response = self.client.get(
            f"/community/notifications/{notification.pk}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_mark_notification_read_requires_post(self):
        notification = AppNotification.objects.create(
            recipient=self.resident_user,
            title="Test notification",
            message="Test message",
        )

        self.client.force_login(self.resident_user)
        response = self.client.get(
            f"/community/notifications/{notification.pk}/mark-read/"
        )

        self.assertEqual(response.status_code, 405)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_notification_read_sets_timestamp(self):
        notification = AppNotification.objects.create(
            recipient=self.resident_user,
            title="Test notification",
            message="Test message",
        )

        self.client.force_login(self.resident_user)
        response = self.client.post(
            f"/community/notifications/{notification.pk}/mark-read/"
        )

        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
