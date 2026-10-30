"""
ResiCare fictional demo-data generator.
Run from the folder containing manage.py:
    python populate_test_data.py

Preserves existing users, apartments, and resident profiles.
Demo records are marked [DEMO] or have Demo-prefixed names.
"""
import os
from datetime import datetime, date, time, timedelta
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.db import transaction
from django.utils import timezone
from accounts.models import User
from residents.models import Apartment, ResidentProfile
from visitors.models import VisitorInvitation, VisitorLog
from maintenance.models import MaintenanceRequest
from facilities.models import Facility, FacilityBooking
from community_hub.models import (
    Notice, CommunityEvent, Delivery, IncidentReport, GateEntry,
    MaintenanceCharge, MaintenancePayment, AppNotification,
)


def get_or_create(model, lookup, defaults):
    return model.objects.get_or_create(**lookup, defaults=defaults)


@transaction.atomic
def populate():
    residents = list(
        ResidentProfile.objects.select_related("user", "apartment")
        .filter(user__role=User.Role.RESIDENT, user__is_active=True).order_by("id")
    )
    security_users = list(User.objects.filter(role=User.Role.SECURITY, is_active=True).order_by("id"))
    managers = list(User.objects.filter(role=User.Role.MANAGEMENT, is_active=True).order_by("id"))
    if not residents or not security_users or not managers:
        raise RuntimeError(
            "Required accounts missing. Ensure active resident profiles, at least one "
            "SECURITY user, and at least one MANAGEMENT user exist."
        )

    today, now = timezone.localdate(), timezone.now()
    security, manager = security_users[0], managers[0]
    created = {}

    def record(label, before, after):
        created[label] = after - before

    # Facilities
    specs = [
        ("Demo Community Hall", "Hall for resident gatherings.", "Clubhouse, Ground Floor", 80, time(8), time(22)),
        ("Demo Fitness Room", "Shared fitness room for residents.", "Block A, Ground Floor", 20, time(5), time(22)),
        ("Demo Indoor Games Room", "Indoor recreation area.", "Clubhouse, First Floor", 25, time(8), time(21)),
        ("Demo Guest Suite", "Guest accommodation subject to approval.", "Block B, Ground Floor", 4, time(9), time(20)),
    ]
    before = Facility.objects.filter(name__startswith="Demo ").count()
    facilities = []
    for name, desc, loc, cap, opening, closing in specs:
        obj, _ = get_or_create(Facility, {"name": name}, {
            "description": desc, "location": loc, "capacity": cap,
            "opening_time": opening, "closing_time": closing, "is_active": True,
        })
        facilities.append(obj)
    record("Facilities", before, Facility.objects.filter(name__startswith="Demo ").count())

    # Notices and events
    notice_specs = [
        ("Water Tank Cleaning", "Water tank cleaning is scheduled; please store water in advance.", "ALL", True),
        ("Parking Reminder", "Park only in your assigned parking space.", "RESIDENT", True),
        ("Security Drill", "A routine safety drill will take place at the main entrance.", "ALL", True),
        ("Security Duty Update", "Review the updated gate duty roster with management.", "SECURITY", False),
        ("Management Review", "Review open requests and resident feedback.", "MANAGEMENT", True),
    ]
    before = Notice.objects.filter(title__startswith="[DEMO] ").count()
    for title, content, audience, published in notice_specs:
        get_or_create(Notice, {"title": f"[DEMO] {title}"}, {
            "content": content, "audience": audience,
            "is_published": published, "author": manager,
        })
    record("Notices", before, Notice.objects.filter(title__startswith="[DEMO] ").count())

    event_specs = [
        ("Residents' Meet", "Monthly gathering for residents.", "Community Hall", 3, "ALL", True),
        ("Yoga Session", "Guided wellness session.", "Open Terrace", 5, "RESIDENT", True),
        ("Fire Safety Awareness", "Fire safety and evacuation guidance.", "Main Courtyard", 7, "ALL", True),
        ("Security Briefing", "Review gate procedures and visitor registration.", "Security Office", 9, "SECURITY", False),
    ]
    before = CommunityEvent.objects.filter(title__startswith="[DEMO] ").count()
    for title, desc, venue, offset, audience, published in event_specs:
        start = timezone.make_aware(datetime.combine(today + timedelta(days=offset), time(17)))
        end = start + timedelta(hours=1, minutes=30)
        get_or_create(CommunityEvent, {"title": f"[DEMO] {title}"}, {
            "description": desc, "venue": venue, "starts_at": start, "ends_at": end,
            "audience": audience, "is_published": published, "author": manager,
        })
    record("Community events", before, CommunityEvent.objects.filter(title__startswith="[DEMO] ").count())

    # Visitor invitations: statuses and reviewer fields are consistent.
    visitor_specs = [
        ("Arun Kumar", "9876501001", "Family visit", VisitorInvitation.Status.PENDING),
        ("Priya S", "9876501002", "Personal visit", VisitorInvitation.Status.APPROVED),
        ("Karthik R", "9876501003", "Delivery", VisitorInvitation.Status.REJECTED),
        ("Meena Devi", "9876501004", "Repair service", VisitorInvitation.Status.CANCELLED),
        ("Rahul N", "9876501005", "Friend visiting", VisitorInvitation.Status.APPROVED),
        ("Sanjay P", "9876501006", "Appliance repair", VisitorInvitation.Status.PENDING),
        ("Divya M", "9876501007", "Family visit", VisitorInvitation.Status.APPROVED),
        ("Vijay T", "9876501008", "Parcel delivery", VisitorInvitation.Status.REJECTED),
    ]
    before = VisitorInvitation.objects.filter(visitor_name__in=[s[0] for s in visitor_specs]).count()
    invitations = []
    for i, (name, phone, purpose, status) in enumerate(visitor_specs):
        reviewed = status in (VisitorInvitation.Status.APPROVED, VisitorInvitation.Status.REJECTED)
        obj, _ = get_or_create(VisitorInvitation, {
            "resident": residents[i % len(residents)], "visitor_name": name, "purpose": purpose,
        }, {
            "visitor_phone": phone, "expected_at": now + timedelta(days=2 + i, hours=i),
            "status": status, "reviewed_by": manager if reviewed else None,
            "reviewed_at": now if reviewed else None,
        })
        invitations.append(obj)
    record("Visitor invitations", before, VisitorInvitation.objects.filter(visitor_name__in=[s[0] for s in visitor_specs]).count())

    before = VisitorLog.objects.filter(visitor_name__startswith="Demo Visitor ").count()
    for i in range(8):
        resident = residents[i % len(residents)]
        entry = now - timedelta(hours=i + 1)
        checked_out = i % 3 != 0
        get_or_create(VisitorLog, {"visitor_name": f"Demo Visitor {i+1:02d}"}, {
            "invitation": invitations[i] if i % 2 == 0 else None,
            "resident": resident, "visitor_phone": f"987651{i:04d}",
            "purpose": ["Personal visit", "Courier delivery", "Repair service", "Family visit"][i % 4],
            "entry_at": entry,
            "exit_at": entry + timedelta(minutes=30) if checked_out else None,
            "checked_in_by": security, "checked_out_by": security if checked_out else None,
            "notes": "Fictional demo visitor log.",
        })
    record("Visitor logs", before, VisitorLog.objects.filter(visitor_name__startswith="Demo Visitor ").count())

    # Maintenance requests across all categories and status types.
    requests = [
        ("Kitchen tap leaking", "PLUMBING", "Water is dripping from the kitchen tap.", "MEDIUM", "SUBMITTED"),
        ("Corridor light failure", "ELECTRICAL", "Corridor light is not working.", "LOW", "IN_PROGRESS"),
        ("Lift noise", "LIFT", "Unusual noise while lift is operating.", "HIGH", "IN_PROGRESS"),
        ("Low water pressure", "WATER", "Water pressure has been low.", "HIGH", "ON_HOLD"),
        ("Common-area cleaning", "CLEANING", "Clean the shared stairway.", "LOW", "RESOLVED"),
        ("Entrance lock inspection", "SECURITY", "Common entrance lock needs inspection.", "URGENT", "CLOSED"),
        ("Bathroom pipe blockage", "PLUMBING", "Bathroom water drains slowly.", "MEDIUM", "SUBMITTED"),
        ("Power socket issue", "ELECTRICAL", "A socket is not working.", "HIGH", "RESOLVED"),
        ("Noticeboard fixture", "OTHER", "Inspect the shared noticeboard fixture.", "LOW", "SUBMITTED"),
    ]
    before = MaintenanceRequest.objects.filter(title__startswith="[DEMO] ").count()
    for i, (title, category, desc, priority, status) in enumerate(requests):
        done = status in ("RESOLVED", "CLOSED")
        resident = residents[i % len(residents)]
        get_or_create(MaintenanceRequest, {"title": f"[DEMO] {title}"}, {
            "resident": resident, "category": category, "description": desc,
            "location": str(resident.apartment or "Common Area"), "priority": priority,
            "status": status, "assigned_to": security if status != "SUBMITTED" else None,
            "resolution_notes": "Demo issue inspected and recorded." if done else "",
            "resolved_at": now - timedelta(hours=3) if done else None,
        })
    record("Maintenance requests", before, MaintenanceRequest.objects.filter(title__startswith="[DEMO] ").count())

    # Facility bookings use future dates and distinct days to avoid conflicts.
    booking_statuses = ["PENDING", "APPROVED", "REJECTED", "CANCELLED", "APPROVED", "PENDING", "REJECTED", "APPROVED"]
    before = FacilityBooking.objects.filter(purpose__startswith="[DEMO] ").count()
    for i, status in enumerate(booking_statuses):
        facility = facilities[i % len(facilities)]
        opening_hour = facility.opening_time.hour
        closing_hour = facility.closing_time.hour
        start_hour = min(max(opening_hour, 10 + (i % 3) * 2), closing_hour - 2)
        start_t, end_t = time(start_hour), time(start_hour + 1)
        reviewed = status in ("APPROVED", "REJECTED")
        get_or_create(FacilityBooking, {"purpose": f"[DEMO] Booking {i+1:02d}"}, {
            "facility": facility, "resident": residents[i % len(residents)],
            "booking_date": today + timedelta(days=10 + i),
            "start_time": start_t, "end_time": end_t, "status": status,
            "reviewed_by": manager if reviewed else None, "reviewed_at": now if reviewed else None,
            "management_notes": "Fictional demo booking.",
        })
    record("Facility bookings", before, FacilityBooking.objects.filter(purpose__startswith="[DEMO] ").count())

    # Deliveries with coherent status-related timestamps.
    deliveries = [
        ("Demo Courier Express", "Parcel", "RECEIVED"),
        ("Demo Grocery Store", "Grocery package", "NOTIFIED"),
        ("Demo Document Service", "Documents", "COLLECTED"),
        ("Demo Online Retailer", "Household items", "RETURNED"),
        ("Demo Pharmacy", "Sealed package", "NOTIFIED"),
        ("Demo Book Shop", "Books", "COLLECTED"),
    ]
    before = Delivery.objects.filter(sender_name__startswith="Demo ").count()
    for i, (sender, description, status) in enumerate(deliveries):
        notified = status in ("NOTIFIED", "COLLECTED")
        collected = status == "COLLECTED"
        get_or_create(Delivery, {"sender_name": sender, "description": description}, {
            "resident": residents[i % len(residents)], "tracking_number": f"DEMO-PARCEL-{i+1:04d}",
            "status": status, "notes": "Fictional demo delivery.", "received_by": security,
            "collected_by": residents[i % len(residents)].user if collected else None,
            "notified_at": now - timedelta(hours=2) if notified else None,
            "collected_at": now - timedelta(hours=1) if collected else None,
        })
    record("Deliveries", before, Delivery.objects.filter(sender_name__startswith="Demo ").count())

    # Incidents
    incidents = [
        ("Unidentified person near parking", "SUSPICIOUS_ACTIVITY", "MEDIUM", "REPORTED"),
        ("Bicycle reported missing", "THEFT", "HIGH", "INVESTIGATING"),
        ("Damaged corridor railing", "PROPERTY_DAMAGE", "LOW", "RESOLVED"),
        ("Smoke alarm inspection", "FIRE", "CRITICAL", "CLOSED"),
        ("Resident assistance", "MEDICAL", "HIGH", "RESOLVED"),
        ("Late-night noise complaint", "NOISE", "LOW", "REPORTED"),
        ("Wet floor near entrance", "SAFETY", "MEDIUM", "INVESTIGATING"),
        ("Other safety observation", "OTHER", "LOW", "CLOSED"),
    ]
    before = IncidentReport.objects.filter(title__startswith="[DEMO] ").count()
    for i, (title, category, severity, status) in enumerate(incidents):
        done = status in ("RESOLVED", "CLOSED")
        get_or_create(IncidentReport, {"title": f"[DEMO] {title}"}, {
            "category": category, "severity": severity,
            "location": ["Main Gate", "Block A parking", "Block B corridor", "Clubhouse"][i % 4],
            "description": f"Fictional test incident report: {title.lower()}.",
            "status": status, "reported_by": residents[i % len(residents)].user,
            "assigned_to": security if status != "REPORTED" else None,
            "resolution_notes": "Demo report reviewed and closed." if done else "",
            "resolved_at": now - timedelta(hours=3) if done else None,
        })
    record("Incident reports", before, IncidentReport.objects.filter(title__startswith="[DEMO] ").count())

    # Gate entries
    before = GateEntry.objects.filter(person_name__startswith="Demo Gate Person ").count()
    for i in range(8):
        entry_type = ["VISITOR", "VEHICLE", "SERVICE_PERSON"][i % 3]
        exited = i % 3 != 0
        entry_time = now - timedelta(hours=i + 1)
        get_or_create(GateEntry, {"person_name": f"Demo Gate Person {i+1:02d}"}, {
            "entry_type": entry_type, "phone_number": f"987652{i:04d}",
            "vehicle_number": f"TN 37 AB {1000+i}" if entry_type == "VEHICLE" else "",
            "vehicle_type": "Car" if entry_type == "VEHICLE" else "",
            "organization": "Demo Service Company" if entry_type == "SERVICE_PERSON" else "",
            "purpose": {"VISITOR": "Resident visit", "VEHICLE": "Vehicle entry",
                        "SERVICE_PERSON": "Repair service"}[entry_type],
            "resident": residents[i % len(residents)],
            "status": "EXITED" if exited else "INSIDE",
            "recorded_by": security, "exit_recorded_by": security if exited else None,
            "exit_time": entry_time + timedelta(minutes=35) if exited else None,
            "notes": "Fictional demo gate entry.",
        })
    record("Gate entries", before, GateEntry.objects.filter(person_name__startswith="Demo Gate Person ").count())

    # Monthly charges: respect the unique apartment/month constraint.
    # Add sample payments only once per charge and never exceed amount_due.
    before = MaintenanceCharge.objects.filter(description="Demo Monthly Maintenance").count()
    month = today.replace(day=1)
    for i, apartment in enumerate(Apartment.objects.filter(is_active=True).order_by("id")):
        charge, _ = get_or_create(MaintenanceCharge, {
            "apartment": apartment, "billing_month": month,
        }, {
            "description": "Demo Monthly Maintenance", "amount_due": Decimal("1500.00"),
            "due_date": month + timedelta(days=9), "notes": "Fictional demo maintenance charge.",
            "created_by": manager,
        })
        if not charge.payments.filter(notes="ResiCare demo payment").exists():
            amount = (charge.amount_due if i % 4 == 0 else
                      min(Decimal("500.00"), charge.amount_due) if i % 4 == 1 else Decimal("0.00"))
            if amount > 0:
                MaintenancePayment.objects.create(
                    charge=charge, amount=amount,
                    payment_method=["UPI", "CASH", "BANK_TRANSFER"][i % 3],
                    reference_number=f"DEMO-PAY-{charge.pk:05d}",
                    notes="ResiCare demo payment", received_by=manager,
                )
    record("Maintenance charges", before, MaintenanceCharge.objects.filter(description="Demo Monthly Maintenance").count())

    # Notifications
    notifications = [
        ("Notice published", "A new community notice is available.", "NOTICE", False),
        ("Event reminder", "A community event is coming up soon.", "EVENT", False),
        ("Parcel received", "A parcel has been received at the gate.", "DELIVERY", True),
        ("Maintenance update", "Your maintenance request status has changed.", "MAINTENANCE", False),
        ("Payment recorded", "A maintenance payment has been recorded.", "PAYMENT", True),
        ("Incident update", "A reported incident has been reviewed.", "INCIDENT", False),
        ("Community update", "Please check the latest community information.", "GENERAL", True),
    ]
    before = AppNotification.objects.filter(title__startswith="[DEMO] ").count()
    for i, (title, message, category, is_read) in enumerate(notifications):
        get_or_create(AppNotification, {
            "recipient": residents[i % len(residents)].user, "title": f"[DEMO] {title}",
        }, {
            "message": message, "category": category, "target_url": "",
            "is_read": is_read, "read_at": now - timedelta(hours=1) if is_read else None,
        })
    record("Notifications", before, AppNotification.objects.filter(title__startswith="[DEMO] ").count())

    print("\nResiCare demo data population completed.")
    print("Existing users, apartments, and resident profiles were preserved.")
    print("\nRecords created this run (0 means the record already existed):")
    for label, amount in created.items():
        print(f"  {label}: {amount}")
    print("\nNote: demo records are fictional and are marked with [DEMO] or Demo-prefixed names.")


if __name__ == "__main__":
    populate()
