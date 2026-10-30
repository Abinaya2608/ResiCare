
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from residents.models import ResidentProfile
from .forms import VisitorInvitationForm, WalkInVisitorForm
from .models import VisitorInvitation, VisitorLog


def require_role(user, *roles):
    if user.role not in roles:
        raise PermissionDenied(
            "You do not have permission to perform this action."
        )


@login_required
def visitor_dashboard(request):
    user = request.user

    if user.role == "RESIDENT":
        profile = ResidentProfile.objects.filter(user=user).first()

        if profile is None:
            raise PermissionDenied(
                "Your resident profile must be created by management."
            )

        invitations = VisitorInvitation.objects.filter(
            resident=profile
        ).select_related("resident__user", "reviewed_by")

        logs = VisitorLog.objects.filter(
            resident=profile
        ).select_related(
            "resident__user",
            "checked_in_by",
            "checked_out_by",
        )

    elif user.role == "SECURITY":
        invitations = VisitorInvitation.objects.filter(
            status=VisitorInvitation.Status.APPROVED
        ).select_related("resident__user", "reviewed_by")

        logs = VisitorLog.objects.all().select_related(
            "resident__user",
            "checked_in_by",
            "checked_out_by",
        )

    elif user.role == "MANAGEMENT":
        invitations = VisitorInvitation.objects.all().select_related(
            "resident__user",
            "reviewed_by",
        )

        logs = VisitorLog.objects.all().select_related(
            "resident__user",
            "checked_in_by",
            "checked_out_by",
        )

    else:
        raise PermissionDenied("Your account role is not supported.")

    # Count visitors who have entered but have not checked out.
    currently_inside = logs.filter(
        entry_at__isnull=False,
        exit_at__isnull=True,
    ).count()

    # Management review queue.
    pending_invitations = invitations.filter(
        status=VisitorInvitation.Status.PENDING
    )

    context = {
        "invitations": invitations,
        "logs": logs,
        "role": user.role,
        "currently_inside": currently_inside,
        "pending_invitations": pending_invitations,
    }

    return render(request, "visitors/dashboard.html", context)


@login_required
def create_invitation(request):
    require_role(request.user, "RESIDENT")

    profile = ResidentProfile.objects.filter(
        user=request.user
    ).first()

    if profile is None:
        raise PermissionDenied(
            "Your resident profile must be created by management."
        )

    if request.method == "POST":
        form = VisitorInvitationForm(request.POST)

        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.resident = profile
            invitation.status = VisitorInvitation.Status.PENDING
            invitation.save()

            messages.success(
                request,
                "Visitor invitation submitted for management review.",
            )
            return redirect("visitors:dashboard")
    else:
        form = VisitorInvitationForm()

    return render(
        request,
        "visitors/create_invitation.html",
        {"form": form},
    )


@login_required
@require_POST
def review_invitation(request, invitation_id):
    require_role(request.user, "MANAGEMENT")

    with transaction.atomic():
        invitation = get_object_or_404(
            VisitorInvitation.objects.select_for_update(),
            pk=invitation_id,
        )

        if invitation.status != VisitorInvitation.Status.PENDING:
            messages.warning(
                request,
                "Only pending invitations can be reviewed.",
            )
            return redirect("visitors:dashboard")

        action = request.POST.get("action")

        if action == "approve":
            invitation.status = VisitorInvitation.Status.APPROVED
        elif action == "reject":
            invitation.status = VisitorInvitation.Status.REJECTED
        else:
            messages.error(request, "Invalid review action.")
            return redirect("visitors:dashboard")

        invitation.reviewed_by = request.user
        invitation.reviewed_at = timezone.now()

        invitation.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

    messages.success(
        request,
        f"Invitation {invitation.get_status_display().lower()}.",
    )
    return redirect("visitors:dashboard")


@login_required
@require_POST
def cancel_invitation(request, invitation_id):
    require_role(request.user, "RESIDENT")

    profile = ResidentProfile.objects.filter(
        user=request.user
    ).first()

    if profile is None:
        raise PermissionDenied("Resident profile not found.")

    with transaction.atomic():
        invitation = get_object_or_404(
            VisitorInvitation.objects.select_for_update(),
            pk=invitation_id,
            resident=profile,
        )

        if invitation.status != VisitorInvitation.Status.PENDING:
            messages.error(
                request,
                "Only pending invitations can be cancelled.",
            )
        else:
            invitation.status = VisitorInvitation.Status.CANCELLED
            invitation.save(
                update_fields=["status", "updated_at"]
            )
            messages.success(request, "Invitation cancelled.")

    return redirect("visitors:dashboard")


@login_required
@require_POST
def check_in_visitor(request, invitation_id):
    require_role(request.user, "SECURITY")

    with transaction.atomic():
        invitation = get_object_or_404(
            VisitorInvitation.objects.select_for_update(),
            pk=invitation_id,
        )

        if invitation.status != VisitorInvitation.Status.APPROVED:
            messages.error(
                request,
                "Only approved invitations can be checked in.",
            )
            return redirect("visitors:dashboard")

        already_inside = VisitorLog.objects.filter(
            invitation=invitation,
            entry_at__isnull=False,
            exit_at__isnull=True,
        ).exists()

        if already_inside:
            messages.warning(
                request,
                "This visitor is already checked in.",
            )
            return redirect("visitors:dashboard")

        VisitorLog.objects.create(
            invitation=invitation,
            resident=invitation.resident,
            visitor_name=invitation.visitor_name,
            visitor_phone=invitation.visitor_phone,
            purpose=invitation.purpose,
            entry_at=timezone.now(),
            checked_in_by=request.user,
        )

    messages.success(request, "Visitor entry recorded.")
    return redirect("visitors:dashboard")


@login_required
@require_POST
def check_out_visitor(request, log_id):
    require_role(request.user, "SECURITY")

    with transaction.atomic():
        visitor_log = get_object_or_404(
            VisitorLog.objects.select_for_update(),
            pk=log_id,
        )

        if visitor_log.entry_at is None:
            messages.error(
                request,
                "This visitor has no recorded entry.",
            )
        elif visitor_log.exit_at is not None:
            messages.warning(
                request,
                "This visitor has already checked out.",
            )
        else:
            visitor_log.exit_at = timezone.now()
            visitor_log.checked_out_by = request.user

            visitor_log.save(
                update_fields=["exit_at", "checked_out_by"]
            )
            messages.success(request, "Visitor exit recorded.")

    return redirect("visitors:dashboard")


@login_required
def walk_in_checkin(request):
    require_role(request.user, "SECURITY")

    if request.method == "POST":
        form = WalkInVisitorForm(request.POST)

        if form.is_valid():
            visitor_log = form.save(commit=False)
            visitor_log.invitation = None
            visitor_log.entry_at = timezone.now()
            visitor_log.checked_in_by = request.user
            visitor_log.save()

            messages.success(
                request,
                "Walk-in visitor entry recorded.",
            )
            return redirect("visitors:dashboard")
    else:
        form = WalkInVisitorForm()

    return render(
        request,
        "visitors/walk_in_checkin.html",
        {"form": form},
    )
