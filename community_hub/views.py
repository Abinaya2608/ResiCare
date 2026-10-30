from .services import send_notification
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import GateEntryForm
from .models import GateEntry
from django.views.decorators.http import require_POST
from .models import AppNotification
from residents.models import ResidentProfile
from .forms import NoticeForm, CommunityEventForm, DeliveryForm
from .models import Notice, CommunityEvent, Delivery
from django.db import IntegrityError, transaction
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from collections import Counter
from django.db.models import Sum

from visitors.models import VisitorInvitation, VisitorLog
from maintenance.models import MaintenanceRequest
from facilities.models import FacilityBooking
from .forms import MaintenanceChargeForm, MaintenancePaymentForm
from .models import MaintenanceCharge, MaintenancePayment


from .forms import (
    NoticeForm,
    CommunityEventForm,
    DeliveryForm,
    IncidentReportForm,
    IncidentUpdateForm,
)
from .models import (
    Notice,
    CommunityEvent,
    Delivery,
    IncidentReport,
)



def is_management(user):
    return user.role == "MANAGEMENT"


def is_delivery_staff(user):
    return user.role in {"MANAGEMENT", "SECURITY"}


def visible_items(queryset, user):
    if is_management(user):
        return queryset

    return queryset.filter(
        is_published=True
    ).filter(
        Q(audience="ALL") | Q(audience=user.role)
    )


def require_management(user):
    if not is_management(user):
        raise PermissionDenied


def get_resident_profile(user):
    try:
        return user.resident_profile
    except ResidentProfile.DoesNotExist:
        return None


@login_required
def community_dashboard(request):
    notices = visible_items(
        Notice.objects.select_related("author"), request.user
    )
    events = visible_items(
        CommunityEvent.objects.select_related("author"), request.user
    )

    return render(request, "community/dashboard.html", {
        "notices": notices,
        "events": events,
        "is_management": is_management(request.user),
    })


@login_required
def notice_detail(request, notice_id):
    notice = get_object_or_404(
        Notice.objects.select_related("author"), pk=notice_id
    )

    if not visible_items(
        Notice.objects.filter(pk=notice.pk), request.user
    ).exists():
        raise PermissionDenied

    return render(request, "community/notice_detail.html", {
        "notice": notice,
        "is_management": is_management(request.user),
    })


@login_required
def create_notice(request):
    require_management(request.user)
    form = NoticeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        notice = form.save(commit=False)
        notice.author = request.user
        notice.save()
        messages.success(request, "Notice created successfully.")
        return redirect("community:dashboard")

    return render(request, "community/notice_form.html", {
        "form": form,
        "page_title": "Create Notice",
    })


@login_required
def edit_notice(request, notice_id):
    require_management(request.user)
    notice = get_object_or_404(Notice, pk=notice_id)
    form = NoticeForm(request.POST or None, instance=notice)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notice updated successfully.")
        return redirect("community:dashboard")

    return render(request, "community/notice_form.html", {
        "form": form,
        "page_title": "Edit Notice",
    })


@login_required
def delete_notice(request, notice_id):
    require_management(request.user)
    notice = get_object_or_404(Notice, pk=notice_id)

    if request.method == "POST":
        notice.delete()
        messages.success(request, "Notice deleted successfully.")
        return redirect("community:dashboard")

    return render(request, "community/confirm_delete.html", {
        "item": notice,
        "cancel_url": "community:dashboard",
    })


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(
        CommunityEvent.objects.select_related("author"), pk=event_id
    )

    if not visible_items(
        CommunityEvent.objects.filter(pk=event.pk), request.user
    ).exists():
        raise PermissionDenied

    return render(request, "community/event_detail.html", {
        "event": event,
        "is_management": is_management(request.user),
    })


@login_required
def create_event(request):
    require_management(request.user)
    form = CommunityEventForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.author = request.user
        event.save()
        messages.success(request, "Event created successfully.")
        return redirect("community:dashboard")

    return render(request, "community/event_form.html", {
        "form": form,
        "page_title": "Create Event",
    })


@login_required
def edit_event(request, event_id):
    require_management(request.user)
    event = get_object_or_404(CommunityEvent, pk=event_id)
    form = CommunityEventForm(request.POST or None, instance=event)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Event updated successfully.")
        return redirect("community:dashboard")

    return render(request, "community/event_form.html", {
        "form": form,
        "page_title": "Edit Event",
    })


@login_required
def delete_event(request, event_id):
    require_management(request.user)
    event = get_object_or_404(CommunityEvent, pk=event_id)

    if request.method == "POST":
        event.delete()
        messages.success(request, "Event deleted successfully.")
        return redirect("community:dashboard")

    return render(request, "community/confirm_delete.html", {
        "item": event,
        "cancel_url": "community:dashboard",
    })


# DELIVERY MANAGEMENT

@login_required
def deliveries(request):
    user = request.user

    if is_delivery_staff(user):
        delivery_list = Delivery.objects.select_related(
            "resident__user",
            "resident__apartment",
            "received_by",
            "collected_by",
        )
    elif user.role == "RESIDENT":
        profile = get_resident_profile(user)
        if profile is None:
            messages.error(request, "Your resident profile has not been created.")
            return redirect("dashboard")

        delivery_list = Delivery.objects.filter(
            resident=profile
        ).select_related(
            "resident__user",
            "resident__apartment",
            "received_by",
            "collected_by",
        )
    else:
        raise PermissionDenied

    status_filter = request.GET.get("status", "")
    valid_statuses = Delivery.Status.values

    if status_filter in valid_statuses:
        delivery_list = delivery_list.filter(status=status_filter)

    context = {
        "deliveries": delivery_list,
        "role": user.role,
        "status_filter": status_filter,
        "status_choices": Delivery.Status.choices,
        "total_count": delivery_list.count(),
        "pending_count": delivery_list.filter(
            status__in=[
                Delivery.Status.RECEIVED,
                Delivery.Status.NOTIFIED,
            ]
        ).count(),
        "collected_count": delivery_list.filter(
            status=Delivery.Status.COLLECTED
        ).count(),
    }

    return render(request, "community/deliveries.html", context)


@login_required
def create_delivery(request):
    if not is_delivery_staff(request.user):
        raise PermissionDenied

    form = DeliveryForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        delivery = form.save(commit=False)
        delivery.status = Delivery.Status.RECEIVED
        delivery.received_by = request.user
        delivery.save()

        messages.success(
            request,
            "Delivery registered successfully. You can now notify the resident.",
        )
        return redirect("community:delivery_detail", delivery_id=delivery.pk)

    return render(request, "community/delivery_form.html", {
        "form": form,
        "page_title": "Register Delivery",
    })


@login_required
def delivery_detail(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "resident__user",
            "resident__apartment",
            "received_by",
            "collected_by",
        ),
        pk=delivery_id,
    )

    user = request.user
    staff = is_delivery_staff(user)

    if user.role == "RESIDENT":
        profile = get_resident_profile(user)
        if profile is None or delivery.resident_id != profile.pk:
            raise PermissionDenied
    elif not staff:
        raise PermissionDenied

    if request.method == "POST":
        action = request.POST.get("action")

        if staff and action == "notify":
            if delivery.status != Delivery.Status.RECEIVED:
                messages.error(request, "Only newly received deliveries can be marked notified.")
            else:
                delivery.status = Delivery.Status.NOTIFIED
                delivery.notified_at = timezone.now()
                delivery.save(update_fields=["status", "notified_at"])
                messages.success(request, "Resident notification status updated.")

        elif staff and action == "return":
            if delivery.status not in {
                Delivery.Status.RECEIVED,
                Delivery.Status.NOTIFIED,
            }:
                messages.error(request, "This delivery can no longer be returned using this action.")
            else:
                delivery.status = Delivery.Status.RETURNED
                delivery.save(update_fields=["status"])
                messages.success(request, "Delivery marked as returned to sender.")

        elif user.role == "RESIDENT" and action == "collect":
            if delivery.status != Delivery.Status.NOTIFIED:
                messages.error(request, "The delivery must be marked notified before collection.")
            else:
                delivery.status = Delivery.Status.COLLECTED
                delivery.collected_at = timezone.now()
                delivery.collected_by = user
                delivery.save(update_fields=[
                    "status", "collected_at", "collected_by"
                ])
                messages.success(request, "Delivery marked as collected.")

        else:
            raise PermissionDenied

        return redirect("community:delivery_detail", delivery_id=delivery.pk)

    return render(request, "community/delivery_detail.html", {
        "delivery": delivery,
        "is_delivery_staff": staff,
        "is_resident": user.role == "RESIDENT",
    })


# INCIDENT MANAGEMENT

@login_required
def incidents(request):
    user = request.user

    if user.role in {"SECURITY", "MANAGEMENT"}:
        incident_list = IncidentReport.objects.select_related(
            "reported_by",
            "assigned_to",
        )
    elif user.role == "RESIDENT":
        incident_list = IncidentReport.objects.filter(
            reported_by=user
        ).select_related(
            "reported_by",
            "assigned_to",
        )
    else:
        raise PermissionDenied

    status_filter = request.GET.get("status", "")
    severity_filter = request.GET.get("severity", "")

    if status_filter in IncidentReport.Status.values:
        incident_list = incident_list.filter(status=status_filter)

    if severity_filter in IncidentReport.Severity.values:
        incident_list = incident_list.filter(severity=severity_filter)

    context = {
        "incidents": incident_list,
        "role": user.role,
        "status_filter": status_filter,
        "severity_filter": severity_filter,
        "status_choices": IncidentReport.Status.choices,
        "severity_choices": IncidentReport.Severity.choices,
        "total_count": incident_list.count(),
        "open_count": incident_list.exclude(
            status__in=[
                IncidentReport.Status.RESOLVED,
                IncidentReport.Status.CLOSED,
            ]
        ).count(),
        "critical_count": incident_list.filter(
            severity=IncidentReport.Severity.CRITICAL
        ).exclude(
            status=IncidentReport.Status.CLOSED
        ).count(),
    }

    return render(request, "community/incidents.html", context)


@login_required
def create_incident(request):
    if request.user.role not in {"RESIDENT", "SECURITY", "MANAGEMENT"}:
        raise PermissionDenied

    form = IncidentReportForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        incident = form.save(commit=False)
        incident.reported_by = request.user
        incident.status = IncidentReport.Status.REPORTED
        incident.save()

        messages.success(
            request,
            "Incident report submitted successfully.",
        )
        return redirect(
            "community:incident_detail",
            incident_id=incident.pk,
        )

    return render(request, "community/incident_form.html", {
        "form": form,
        "page_title": "Report an Incident",
    })


@login_required
def incident_detail(request, incident_id):
    incident = get_object_or_404(
        IncidentReport.objects.select_related(
            "reported_by",
            "assigned_to",
        ),
        pk=incident_id,
    )

    user = request.user
    is_staff = user.role in {"SECURITY", "MANAGEMENT"}

    if not is_staff and incident.reported_by_id != user.pk:
        raise PermissionDenied

    if request.method == "POST":
        if not is_staff:
            raise PermissionDenied

        form = IncidentUpdateForm(
            request.POST,
            instance=incident,
        )

        if form.is_valid():
            updated_incident = form.save(commit=False)

            if updated_incident.status in {
                IncidentReport.Status.RESOLVED,
                IncidentReport.Status.CLOSED,
            }:
                if not updated_incident.resolved_at:
                    updated_incident.resolved_at = timezone.now()
            else:
                updated_incident.resolved_at = None

            updated_incident.save()

            messages.success(
                request,
                "Incident details updated successfully.",
            )
            return redirect(
                "community:incident_detail",
                incident_id=incident.pk,
            )
    else:
        form = IncidentUpdateForm(instance=incident) if is_staff else None

    return render(request, "community/incident_detail.html", {
        "incident": incident,
        "form": form,
        "is_staff": is_staff,
    })


# VEHICLE AND SERVICE PERSONNEL LOGS

@login_required
def gate_logs(request):
    if request.user.role not in {"SECURITY", "MANAGEMENT"}:
        raise PermissionDenied

    entries = GateEntry.objects.select_related(
        "resident__user",
        "resident__apartment",
        "recorded_by",
        "exit_recorded_by",
    )

    entry_type = request.GET.get("type", "")
    status = request.GET.get("status", "")
    search = request.GET.get("q", "").strip()

    if entry_type in GateEntry.EntryType.values:
        entries = entries.filter(entry_type=entry_type)

    if status in GateEntry.Status.values:
        entries = entries.filter(status=status)

    if search:
        entries = entries.filter(
            Q(person_name__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(vehicle_number__icontains=search)
            | Q(organization__icontains=search)
            | Q(purpose__icontains=search)
        )

    context = {
        "entries": entries,
        "type_choices": GateEntry.EntryType.choices,
        "status_choices": GateEntry.Status.choices,
        "selected_type": entry_type,
        "selected_status": status,
        "search_query": search,
        "total_count": entries.count(),
        "inside_count": entries.filter(
            status=GateEntry.Status.INSIDE
        ).count(),
        "exited_count": entries.filter(
            status=GateEntry.Status.EXITED
        ).count(),
    }

    return render(request, "community/gate_logs.html", context)


@login_required
def create_gate_entry(request):
    if request.user.role not in {"SECURITY", "MANAGEMENT"}:
        raise PermissionDenied

    form = GateEntryForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.status = GateEntry.Status.INSIDE
        entry.entry_time = timezone.now()
        entry.recorded_by = request.user
        entry.exit_time = None
        entry.exit_recorded_by = None
        entry.save()

        messages.success(
            request,
            "Gate entry recorded successfully.",
        )
        return redirect(
            "community:gate_entry_detail",
            entry_id=entry.pk,
        )

    return render(request, "community/gate_entry_form.html", {
        "form": form,
        "page_title": "Record Gate Entry",
    })


@login_required
def gate_entry_detail(request, entry_id):
    if request.user.role not in {"SECURITY", "MANAGEMENT"}:
        raise PermissionDenied

    entry = get_object_or_404(
        GateEntry.objects.select_related(
            "resident__user",
            "resident__apartment",
            "recorded_by",
            "exit_recorded_by",
        ),
        pk=entry_id,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "mark_exit":
            if entry.status == GateEntry.Status.EXITED:
                messages.info(request, "This entry has already been marked as exited.")
            else:
                entry.status = GateEntry.Status.EXITED
                entry.exit_time = timezone.now()
                entry.exit_recorded_by = request.user
                entry.save()

                messages.success(
                    request,
                    "Exit time recorded successfully.",
                )

        else:
            raise PermissionDenied

        return redirect(
            "community:gate_entry_detail",
            entry_id=entry.pk,
        )

    return render(request, "community/gate_entry_detail.html", {
        "entry": entry,
    })

# MAINTENANCE DUES AND PAYMENTS

def get_resident_apartment(user):
    profile = get_resident_profile(user)
    if profile is None:
        return None
    return profile.apartment


@login_required
def maintenance_dues(request):
    user = request.user

    if user.role == "MANAGEMENT":
        charges = MaintenanceCharge.objects.select_related(
            "apartment",
            "created_by",
        )
    elif user.role == "RESIDENT":
        apartment = get_resident_apartment(user)

        if apartment is None:
            messages.error(
                request,
                "Your resident profile or apartment assignment is missing.",
            )
            return redirect("dashboard")

        charges = MaintenanceCharge.objects.filter(
            apartment=apartment
        ).select_related("apartment", "created_by")
    else:
        raise PermissionDenied

    status_filter = request.GET.get("status", "")

    # Filter calculated payment status after retrieving the charges.
    charge_list = list(charges)

    if status_filter in {"PENDING", "PARTIAL", "PAID"}:
        charge_list = [
            charge for charge in charge_list
            if charge.payment_status == status_filter
        ]

    context = {
        "charges": charge_list,
        "role": user.role,
        "status_filter": status_filter,
        "total_charges": sum(
            (charge.amount_due for charge in charge_list),
            Decimal("0.00"),
        ),
        "total_paid": sum(
            (charge.total_paid for charge in charge_list),
            Decimal("0.00"),
        ),
        "total_balance": sum(
            (charge.balance_due for charge in charge_list),
            Decimal("0.00"),
        ),
    }

    return render(request, "community/maintenance_dues.html", context)


@login_required
def create_maintenance_charge(request):
    if request.user.role != "MANAGEMENT":
        raise PermissionDenied

    form = MaintenanceChargeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        charge = form.save(commit=False)
        charge.created_by = request.user

        try:
            with transaction.atomic():
                charge.save()
        except IntegrityError:
            form.add_error(
                None,
                "A maintenance charge already exists for this apartment and month.",
            )
        else:
            messages.success(
                request,
                "Maintenance charge created successfully.",
            )
            return redirect(
                "community:maintenance_charge_detail",
                charge_id=charge.pk,
            )

    return render(request, "community/maintenance_charge_form.html", {
        "form": form,
        "page_title": "Create Maintenance Charge",
    })


@login_required
def maintenance_charge_detail(request, charge_id):
    charge = get_object_or_404(
        MaintenanceCharge.objects.select_related(
            "apartment",
            "created_by",
        ),
        pk=charge_id,
    )

    user = request.user

    if user.role == "RESIDENT":
        apartment = get_resident_apartment(user)

        if apartment is None or apartment.pk != charge.apartment_id:
            raise PermissionDenied
    elif user.role != "MANAGEMENT":
        raise PermissionDenied

    payments = charge.payments.select_related("received_by").all()

    return render(request, "community/maintenance_charge_detail.html", {
        "charge": charge,
        "payments": payments,
        "role": user.role,
    })


@login_required
def record_maintenance_payment(request, charge_id):
    if request.user.role != "MANAGEMENT":
        raise PermissionDenied

    charge = get_object_or_404(
        MaintenanceCharge.objects.select_related("apartment"),
        pk=charge_id,
    )

    if charge.balance_due <= Decimal("0.00"):
        messages.info(request, "This maintenance charge has already been paid.")
        return redirect(
            "community:maintenance_charge_detail",
            charge_id=charge.pk,
        )

    form = MaintenancePaymentForm(
        request.POST or None,
        charge=charge,
    )

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                # Re-fetch the charge inside the transaction to reduce
                # the chance of recording concurrent overpayments.
                locked_charge = MaintenanceCharge.objects.select_for_update().get(
                    pk=charge.pk
                )
                payment = form.save(commit=False)
                payment.charge = locked_charge
                payment.received_by = request.user

                payment.full_clean()
                payment.save()
        except ValidationError as exc:
            if hasattr(exc, "message_dict") and "amount" in exc.message_dict:
                form.add_error("amount", "The payment exceeds the remaining balance.")
            else:
                form.add_error(None, "The payment could not be recorded. Review the entered details.")
        else:
            messages.success(
                request,
                "Payment recorded successfully.",
            )
            return redirect(
                "community:maintenance_charge_detail",
                charge_id=charge.pk,
            )

    return render(request, "community/maintenance_payment_form.html", {
        "form": form,
        "charge": charge,
        "page_title": "Record Maintenance Payment",
    })
    
@login_required
def notifications(request):
    user_notifications = AppNotification.objects.filter(
        recipient=request.user
    )

    unread_count = user_notifications.filter(is_read=False).count()

    return render(
        request,
        "community/notifications.html",
        {
            "notifications": user_notifications,
            "unread_count": unread_count,
        },
    )


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        AppNotification,
        id=notification_id,
        recipient=request.user,
    )

    notification.mark_as_read()
    return redirect("community:notification_open", notification_id=notification.id)


@login_required
@require_POST
def mark_all_notifications_read(request):
    AppNotification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(
        is_read=True,
        read_at=timezone.now(),
    )

    messages.success(request, "All notifications have been marked as read.")
    return redirect("community:notifications")


@login_required
def notification_open(request, notification_id):
    notification = get_object_or_404(
        AppNotification,
        id=notification_id,
        recipient=request.user,
    )

    notification.mark_as_read()

    # Only redirect to a local path, never an external website.
    target = notification.target_url
    if target.startswith("/") and not target.startswith("//"):
        return redirect(target)

    return redirect("community:notifications")


@login_required
def management_reports(request):
    """Operational reports for management and security."""

    role = getattr(request.user, "role", "")

    # Restrict reports to management and security.
    if role not in ("MANAGEMENT", "SECURITY"):
        raise PermissionDenied(
            "Only management and security can access these reports."
        )

    def count_statuses(queryset):
        status_counts = Counter(
            queryset.values_list("status", flat=True)
        )
        return [
            {"status": status, "count": count}
            for status, count in sorted(status_counts.items())
        ]

    # Visitor activity
    invitations = VisitorInvitation.objects.all()
    visitor_logs = VisitorLog.objects.all()

    # Maintenance requests
    maintenance_requests = MaintenanceRequest.objects.all()

    # Facility bookings
    facility_bookings = FacilityBooking.objects.all()

    # Security incidents
    incidents = IncidentReport.objects.all()

    # Parcel deliveries
    deliveries = Delivery.objects.all()

    context = {
        "role": role,

        "visitor_invitation_total": invitations.count(),
        "visitor_log_total": visitor_logs.count(),
        "invitation_statuses": count_statuses(invitations),

        "maintenance_request_total": maintenance_requests.count(),
        "maintenance_statuses": count_statuses(
            maintenance_requests
        ),

        "facility_booking_total": facility_bookings.count(),
        "facility_statuses": count_statuses(facility_bookings),

        "incident_total": incidents.count(),
        "incident_statuses": count_statuses(incidents),

        "delivery_total": deliveries.count(),
        "delivery_statuses": count_statuses(deliveries),

        "pending_deliveries": deliveries.filter(
            status__in=[
                Delivery.Status.RECEIVED,
                Delivery.Status.NOTIFIED,
            ]
        ).count(),
    }

    # Show financial reports to management only.
    if role == "MANAGEMENT":
        charges = list(MaintenanceCharge.objects.all())

        context.update({
            "maintenance_charge_total": len(charges),

            "maintenance_amount_due": sum(
                (charge.amount_due for charge in charges),
                Decimal("0.00"),
            ),

            "maintenance_amount_paid": sum(
                (charge.total_paid for charge in charges),
                Decimal("0.00"),
            ),

            "maintenance_balance": sum(
                (charge.balance_due for charge in charges),
                Decimal("0.00"),
            ),
        })

    return render(
        request,
        "community/management_reports.html",
        context,
    )
