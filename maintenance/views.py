
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from residents.models import ResidentProfile
from .forms import MaintenanceRequestForm, MaintenanceUpdateForm
from .models import MaintenanceRequest


def get_resident_profile(user):
    try:
        return user.resident_profile
    except ResidentProfile.DoesNotExist:
        return None


def can_manage(user):
    return user.role == "MANAGEMENT"


@login_required
def maintenance_dashboard(request):
    user = request.user

    if user.role == "RESIDENT":
        profile = get_resident_profile(user)

        if profile is None:
            messages.error(
                request,
                "Your resident profile has not been created yet.",
            )
            return redirect("dashboard")

        requests = MaintenanceRequest.objects.filter(resident=profile)

    elif user.role == "MANAGEMENT":
        requests = MaintenanceRequest.objects.select_related(
            "resident__user", "assigned_to"
        ).all()

    elif user.role == "SECURITY":
        requests = MaintenanceRequest.objects.filter(
            assigned_to=user
        ).select_related("resident__user", "assigned_to")

    else:
        raise PermissionDenied

    context = {
        "requests_list": requests,
        "total_count": requests.count(),
        "open_count": requests.filter(
            status__in=[
                MaintenanceRequest.Status.SUBMITTED,
                MaintenanceRequest.Status.IN_PROGRESS,
                MaintenanceRequest.Status.ON_HOLD,
            ]
        ).count(),
        "resolved_count": requests.filter(
            status=MaintenanceRequest.Status.RESOLVED
        ).count(),
        "role": user.role,
    }

    return render(
        request,
        "maintenance/dashboard.html",
        context,
    )


@login_required
def create_request(request):
    if request.user.role != "RESIDENT":
        raise PermissionDenied

    profile = get_resident_profile(request.user)

    if profile is None:
        messages.error(
            request,
            "Your resident profile must be created before submitting a complaint.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        form = MaintenanceRequestForm(request.POST)

        if form.is_valid():
            maintenance_request = form.save(commit=False)
            maintenance_request.resident = profile
            maintenance_request.save()

            messages.success(
                request,
                "Your maintenance complaint has been submitted successfully.",
            )
            return redirect("maintenance:dashboard")
    else:
        form = MaintenanceRequestForm()

    return render(
        request,
        "maintenance/create_request.html",
        {"form": form},
    )



@login_required
def request_detail(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest.objects.select_related(
            "resident__user", "assigned_to"
        ),
        pk=request_id,
    )

    user = request.user
    is_management = can_manage(user)
    is_security = user.role == "SECURITY"

    # Check whether the user is allowed to view this request.
    if user.role == "RESIDENT":
        profile = get_resident_profile(user)

        if (
            profile is None
            or maintenance_request.resident_id != profile.id
        ):
            raise PermissionDenied

    elif is_security:
        if maintenance_request.assigned_to_id != user.id:
            raise PermissionDenied

    elif not is_management:
        raise PermissionDenied

    update_form = None

    # Only Management and assigned Security staff can update requests.
    if is_management or is_security:
        if request.method == "POST":
            if is_management:
                update_form = MaintenanceUpdateForm(
                    request.POST,
                    instance=maintenance_request,
                    user=user,
                )
            else:
                update_form = MaintenanceUpdateForm(
                    request.POST,
                    instance=maintenance_request,
                    user=user,
                )

            if update_form.is_valid():
                with transaction.atomic():
                    item = update_form.save(commit=False)

                    # Security must never change the assignment.
                    if is_security:
                        item.assigned_to = maintenance_request.assigned_to

                    if item.status in [
                        MaintenanceRequest.Status.RESOLVED,
                        MaintenanceRequest.Status.CLOSED,
                    ]:
                        if item.resolved_at is None:
                            item.resolved_at = timezone.now()
                    else:
                        item.resolved_at = None

                    item.save()

                messages.success(
                    request,
                    "Maintenance request updated successfully.",
                )
                return redirect(
                    "maintenance:request_detail",
                    request_id=maintenance_request.pk,
                )
        else:
            update_form = MaintenanceUpdateForm(
                instance=maintenance_request,
                user=user,
            )

    return render(
        request,
        "maintenance/request_detail.html",
        {
            "maintenance_request": maintenance_request,
            "update_form": update_form,
            "can_manage": is_management,
            "can_update": is_management or is_security,
        },
    )
