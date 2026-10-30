
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from residents.models import Apartment, ResidentProfile
from .models import VisitorInvitation, VisitorLog

User = get_user_model()


class VisitorPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resident_user = User.objects.create_user(
            username="visitor_resident1",
            password="TestPass123!",
            role="RESIDENT",
        )
        cls.other_resident_user = User.objects.create_user(
            username="visitor_resident2",
            password="TestPass123!",
            role="RESIDENT",
        )
        cls.security_user = User.objects.create_user(
            username="visitor_security",
            password="TestPass123!",
            role="SECURITY",
        )
        cls.management_user = User.objects.create_user(
            username="visitor_manager",
            password="TestPass123!",
            role="MANAGEMENT",
        )

        cls.apartment1 = Apartment.objects.create(
            building_name="Visitor Test Building",
            unit_number="V101",
        )
        cls.apartment2 = Apartment.objects.create(
            building_name="Visitor Test Building",
            unit_number="V102",
        )

        cls.resident_profile = ResidentProfile.objects.create(
            user=cls.resident_user,
            apartment=cls.apartment1,
        )
        cls.other_resident_profile = ResidentProfile.objects.create(
            user=cls.other_resident_user,
            apartment=cls.apartment2,
        )

        cls.pending_invitation = VisitorInvitation.objects.create(
            resident=cls.resident_profile,
            visitor_name="Pending Guest",
            visitor_phone="9876543210",
            purpose="Family visit",
            expected_at=timezone.now() + timedelta(days=1),
        )

        cls.approved_invitation = VisitorInvitation.objects.create(
            resident=cls.resident_profile,
            visitor_name="Approved Guest",
            visitor_phone="9876543211",
            purpose="Family visit",
            expected_at=timezone.now() + timedelta(days=1),
            status=VisitorInvitation.Status.APPROVED,
            reviewed_by=cls.management_user,
            reviewed_at=timezone.now(),
        )

        cls.other_resident_invitation = VisitorInvitation.objects.create(
            resident=cls.other_resident_profile,
            visitor_name="Other Resident Guest",
            visitor_phone="9876543212",
            purpose="Personal visit",
            expected_at=timezone.now() + timedelta(days=1),
        )

    def test_resident_dashboard_shows_only_own_invitations(self):
        self.client.force_login(self.resident_user)

        response = self.client.get(reverse("visitors:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending Guest")
        self.assertNotContains(response, "Other Resident Guest")

    def test_management_can_approve_pending_invitation(self):
        self.client.force_login(self.management_user)

        response = self.client.post(
            reverse(
                "visitors:review_invitation",
                kwargs={"invitation_id": self.pending_invitation.pk},
            ),
            {"action": "approve"},
        )

        self.assertRedirects(response, reverse("visitors:dashboard"))

        self.pending_invitation.refresh_from_db()
        self.assertEqual(
            self.pending_invitation.status,
            VisitorInvitation.Status.APPROVED,
        )
        self.assertEqual(
            self.pending_invitation.reviewed_by,
            self.management_user,
        )
        self.assertIsNotNone(self.pending_invitation.reviewed_at)

    def test_security_cannot_review_invitation(self):
        self.client.force_login(self.security_user)

        response = self.client.post(
            reverse(
                "visitors:review_invitation",
                kwargs={"invitation_id": self.pending_invitation.pk},
            ),
            {"action": "approve"},
        )

        self.assertEqual(response.status_code, 403)

        self.pending_invitation.refresh_from_db()
        self.assertEqual(
            self.pending_invitation.status,
            VisitorInvitation.Status.PENDING,
        )

    def test_resident_cannot_cancel_another_residents_invitation(self):
        self.client.force_login(self.resident_user)

        response = self.client.post(
            reverse(
                "visitors:cancel_invitation",
                kwargs={
                    "invitation_id": self.other_resident_invitation.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

        self.other_resident_invitation.refresh_from_db()
        self.assertEqual(
            self.other_resident_invitation.status,
            VisitorInvitation.Status.PENDING,
        )

    def test_resident_can_cancel_own_pending_invitation(self):
        self.client.force_login(self.resident_user)

        response = self.client.post(
            reverse(
                "visitors:cancel_invitation",
                kwargs={"invitation_id": self.pending_invitation.pk},
            )
        )

        self.assertRedirects(response, reverse("visitors:dashboard"))

        self.pending_invitation.refresh_from_db()
        self.assertEqual(
            self.pending_invitation.status,
            VisitorInvitation.Status.CANCELLED,
        )

    def test_security_can_check_in_approved_visitor(self):
        self.client.force_login(self.security_user)

        response = self.client.post(
            reverse(
                "visitors:check_in",
                kwargs={"invitation_id": self.approved_invitation.pk},
            )
        )

        self.assertRedirects(response, reverse("visitors:dashboard"))

        log = VisitorLog.objects.get(
            invitation=self.approved_invitation
        )
        self.assertEqual(log.checked_in_by, self.security_user)
        self.assertIsNotNone(log.entry_at)
        self.assertIsNone(log.exit_at)

    def test_security_cannot_check_in_pending_invitation(self):
        self.client.force_login(self.security_user)

        response = self.client.post(
            reverse(
                "visitors:check_in",
                kwargs={"invitation_id": self.pending_invitation.pk},
            )
        )

        self.assertRedirects(response, reverse("visitors:dashboard"))
        self.assertFalse(
            VisitorLog.objects.filter(
                invitation=self.pending_invitation
            ).exists()
        )

    def test_resident_cannot_check_in_visitor(self):
        self.client.force_login(self.resident_user)

        response = self.client.post(
            reverse(
                "visitors:check_in",
                kwargs={"invitation_id": self.approved_invitation.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_security_can_check_out_visitor(self):
        log = VisitorLog.objects.create(
            invitation=self.approved_invitation,
            resident=self.resident_profile,
            visitor_name="Approved Guest",
            visitor_phone="9876543211",
            purpose="Family visit",
            entry_at=timezone.now() - timedelta(minutes=30),
            checked_in_by=self.security_user,
        )

        self.client.force_login(self.security_user)

        response = self.client.post(
            reverse(
                "visitors:check_out",
                kwargs={"log_id": log.pk},
            )
        )

        self.assertRedirects(response, reverse("visitors:dashboard"))

        log.refresh_from_db()
        self.assertIsNotNone(log.exit_at)
        self.assertEqual(log.checked_out_by, self.security_user)

    def test_security_can_register_walk_in_visitor(self):
        self.client.force_login(self.security_user)

        response = self.client.post(
            reverse("visitors:walk_in_checkin"),
            {
                "resident": self.resident_profile.pk,
                "visitor_name": "Walk In Guest",
                "visitor_phone": "9876543213",
                "purpose": "Parcel delivery",
                "notes": "Test delivery",
            },
        )

        self.assertRedirects(response, reverse("visitors:dashboard"))

        log = VisitorLog.objects.get(visitor_name="Walk In Guest")
        self.assertIsNone(log.invitation)
        self.assertEqual(log.checked_in_by, self.security_user)
        self.assertIsNotNone(log.entry_at)
        self.assertEqual(log.resident, self.resident_profile)
