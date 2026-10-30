
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from residents.models import Apartment, ResidentProfile
from .models import MaintenanceRequest

User = get_user_model()


class MaintenancePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resident_user = User.objects.create_user(
            username="resident1",
            password="TestPass123!",
            role="RESIDENT",
        )
        cls.other_resident_user = User.objects.create_user(
            username="resident2",
            password="TestPass123!",
            role="RESIDENT",
        )
        cls.security_user = User.objects.create_user(
            username="security1",
            password="TestPass123!",
            role="SECURITY",
        )
        cls.other_security_user = User.objects.create_user(
            username="security2",
            password="TestPass123!",
            role="SECURITY",
        )
        cls.management_user = User.objects.create_user(
            username="manager1",
            password="TestPass123!",
            role="MANAGEMENT",
        )

        cls.apartment1 = Apartment.objects.create(
            building_name="Test Building",
            unit_number="A101",
        )
        cls.apartment2 = Apartment.objects.create(
            building_name="Test Building",
            unit_number="A102",
        )

        cls.resident_profile = ResidentProfile.objects.create(
            user=cls.resident_user,
            apartment=cls.apartment1,
        )
        cls.other_resident_profile = ResidentProfile.objects.create(
            user=cls.other_resident_user,
            apartment=cls.apartment2,
        )

        cls.resident_request = MaintenanceRequest.objects.create(
            resident=cls.resident_profile,
            title="Leaking tap",
            category=MaintenanceRequest.Category.PLUMBING,
            description="The kitchen tap is leaking continuously.",
            location="Flat A101",
            priority=MaintenanceRequest.Priority.MEDIUM,
        )

        cls.other_resident_request = MaintenanceRequest.objects.create(
            resident=cls.other_resident_profile,
            title="Broken light",
            category=MaintenanceRequest.Category.ELECTRICAL,
            description="The corridor light is not working.",
            location="Flat A102",
            priority=MaintenanceRequest.Priority.HIGH,
            assigned_to=cls.other_security_user,
        )

    def test_resident_can_view_maintenance_dashboard(self):
        self.client.force_login(self.resident_user)

        response = self.client.get(
            reverse("maintenance:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leaking tap")
        self.assertNotContains(response, "Broken light")

    def test_security_can_view_assigned_requests_only(self):
        self.client.force_login(self.other_security_user)

        response = self.client.get(
            reverse("maintenance:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Broken light")
        self.assertNotContains(response, "Leaking tap")

    def test_management_can_view_all_requests(self):
        self.client.force_login(self.management_user)

        response = self.client.get(
            reverse("maintenance:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leaking tap")
        self.assertContains(response, "Broken light")

    def test_resident_cannot_view_another_residents_request(self):
        self.client.force_login(self.resident_user)

        response = self.client.get(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.other_resident_request.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_security_cannot_view_unassigned_request(self):
        self.client.force_login(self.security_user)

        response = self.client.get(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.resident_request.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_assigned_security_can_view_request(self):
        self.client.force_login(self.other_security_user)

        response = self.client.get(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.other_resident_request.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_management_can_view_request_detail(self):
        self.client.force_login(self.management_user)

        response = self.client.get(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.resident_request.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

    
    def test_management_can_assign_security_staff(self):
        self.client.force_login(self.management_user)

        response = self.client.post(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.resident_request.pk},
            ),
            {
                "status": MaintenanceRequest.Status.IN_PROGRESS,
                "assigned_to": self.security_user.pk,
                "resolution_notes": "Technician assigned.",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.resident_request.pk},
            ),
        )

        self.resident_request.refresh_from_db()
        self.assertEqual(
            self.resident_request.assigned_to_id,
            self.security_user.pk,
        )
        self.assertEqual(
            self.resident_request.status,
            MaintenanceRequest.Status.IN_PROGRESS,
        )

    def test_assigned_security_can_update_status_and_notes(self):
        self.client.force_login(self.other_security_user)

        response = self.client.post(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.other_resident_request.pk},
            ),
            {
                "status": MaintenanceRequest.Status.RESOLVED,
                "resolution_notes": "The corridor light has been repaired.",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.other_resident_request.pk},
            ),
        )

        self.other_resident_request.refresh_from_db()
        self.assertEqual(
            self.other_resident_request.status,
            MaintenanceRequest.Status.RESOLVED,
        )
        self.assertEqual(
            self.other_resident_request.resolution_notes,
            "The corridor light has been repaired.",
        )
        self.assertIsNotNone(self.other_resident_request.resolved_at)

    def test_security_cannot_reassign_request(self):
        self.client.force_login(self.other_security_user)

        response = self.client.post(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.other_resident_request.pk},
            ),
            {
                "status": MaintenanceRequest.Status.IN_PROGRESS,
                "assigned_to": self.security_user.pk,
                "resolution_notes": "Working on the issue.",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.other_resident_request.pk},
            ),
        )

        self.other_resident_request.refresh_from_db()
        self.assertEqual(
            self.other_resident_request.assigned_to_id,
            self.other_security_user.pk,
        )

    def test_resident_cannot_update_maintenance_request(self):
        self.client.force_login(self.resident_user)

        response = self.client.post(
            reverse(
                "maintenance:request_detail",
                kwargs={"request_id": self.resident_request.pk},
            ),
            {
                "status": MaintenanceRequest.Status.RESOLVED,
                "resolution_notes": "Trying to update my own request.",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.resident_request.refresh_from_db()
        self.assertEqual(
            self.resident_request.status,
            MaintenanceRequest.Status.SUBMITTED,
        )
        self.assertEqual(self.resident_request.resolution_notes, "")
