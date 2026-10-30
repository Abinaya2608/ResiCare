
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from residents.models import ResidentProfile
from .forms import FacilityBookingForm, FacilityBookingReviewForm
from .models import Facility, FacilityBooking


def get_resident_profile(user):
    try:
        return user.resident_profile
    except ResidentProfile.DoesNotExist:
        return None


@login_required
def facility_dashboard(request):
    role = request.user.role

    facilities = Facility.objects.filter(is_active=True)

    bookings = FacilityBooking.objects.select_related(
        "facility",
        "resident__user",
        "reviewed_by",
    )

    if role == "RESIDENT":
        profile = get_resident_profile(request.user)

        if profile is None:
            messages.error(
                request,
                "Your resident profile has not been created yet.",
            )
            return redirect("dashboard")

        bookings = bookings.filter(resident=profile)

    elif role == "MANAGEMENT":
        bookings = bookings.all()

    elif role == "SECURITY":
        bookings = bookings.filter(
            status=FacilityBooking.Status.APPROVED
        )

    else:
        raise PermissionDenied

    context = {
        "facilities": facilities,
        "bookings": bookings,
        "role": role,
        "total_bookings": bookings.count(),
        "pending_count": bookings.filter(
            status=FacilityBooking.Status.PENDING
        ).count(),
        "approved_count": bookings.filter(
            status=FacilityBooking.Status.APPROVED
        ).count(),
    }

    return render(
        request,
        "facilities/dashboard.html",
        context,
    )



@login_required
def create_booking(request):
    if request.user.role != "RESIDENT":
        raise PermissionDenied

    profile = get_resident_profile(request.user)

    if profile is None:
        messages.error(
            request,
            "Your resident profile must be created before booking facilities.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        form = FacilityBookingForm(request.POST)

        if form.is_valid():
            booking = form.save(commit=False)
            booking.resident = profile
            booking.status = FacilityBooking.Status.PENDING

            try:
                booking.full_clean()
                booking.save()
            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errors in exc.message_dict.items():
                        target = field if field in form.fields else None

                        for error in errors:
                            form.add_error(target, error)
                else:
                    for error in exc.messages:
                        form.add_error(None, error)
            else:
                messages.success(
                    request,
                    "Your facility booking request has been submitted for approval.",
                )
                return redirect("facilities:dashboard")
    else:
        form = FacilityBookingForm()

    return render(
        request,
        "facilities/create_booking.html",
        {"form": form},
    )


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        FacilityBooking.objects.select_related(
            "facility",
            "resident__user",
            "reviewed_by",
        ),
        pk=booking_id,
    )

    user = request.user
    role = user.role

    if role == "RESIDENT":
        profile = get_resident_profile(user)

        if profile is None or booking.resident_id != profile.pk:
            raise PermissionDenied

    elif role == "SECURITY":
        if booking.status != FacilityBooking.Status.APPROVED:
            raise PermissionDenied

    elif role != "MANAGEMENT":
        raise PermissionDenied

    review_form = None

    if role == "MANAGEMENT":
        if request.method == "POST":
            action = request.POST.get("action")

            if action not in ["approve", "reject"]:
                messages.error(request, "Invalid booking action.")
                return redirect(
                    "facilities:booking_detail",
                    booking_id=booking.pk,
                )

            if booking.status != FacilityBooking.Status.PENDING:
                messages.error(
                    request,
                    "Only pending bookings can be reviewed.",
                )
                return redirect(
                    "facilities:booking_detail",
                    booking_id=booking.pk,
                )

            review_form = FacilityBookingReviewForm(request.POST)

            if review_form.is_valid():
                with transaction.atomic():
                    # Lock the facility row while checking and approving.
                    facility = get_object_or_404(
                        Facility.objects.select_for_update(),
                        pk=booking.facility_id,
                    )

                    booking = get_object_or_404(
                        FacilityBooking.objects.select_for_update(),
                        pk=booking.pk,
                    )

                    if booking.status != FacilityBooking.Status.PENDING:
                        messages.error(
                            request,
                            "This booking has already been reviewed.",
                        )
                        return redirect(
                            "facilities:booking_detail",
                            booking_id=booking.pk,
                        )

                    booking.management_notes = (
                        review_form.cleaned_data["management_notes"]
                    )
                    booking.reviewed_by = user
                    booking.reviewed_at = timezone.now()

                    if action == "approve":
                        booking.status = FacilityBooking.Status.APPROVED

                        try:
                            booking.full_clean()
                        except ValidationError:
                            booking.status = FacilityBooking.Status.PENDING
                            booking.reviewed_by = None
                            booking.reviewed_at = None
                            messages.error(
                                request,
                                "This time slot conflicts with an existing approved booking. "
                                "Reject this request or ask the resident to choose another time.",
                            )
                            return redirect(
                                "facilities:booking_detail",
                                booking_id=booking.pk,
                            )
                    else:
                        booking.status = FacilityBooking.Status.REJECTED

                    booking.save()

                messages.success(
                    request,
                    f"Booking {booking.get_status_display().lower()} successfully.",
                )
                return redirect(
                    "facilities:booking_detail",
                    booking_id=booking.pk,
                )
        else:
            review_form = FacilityBookingReviewForm(
                instance=booking,
            )

    
    if role == "RESIDENT":
        if request.method == "POST" and request.POST.get("action") == "cancel":
            if booking.status != FacilityBooking.Status.PENDING:
                messages.error(
                    request,
                    "Only pending bookings can be cancelled.",
                )
                return redirect(
                    "facilities:booking_detail",
                    booking_id=booking.pk,
                )

            with transaction.atomic():
                booking = get_object_or_404(
                    FacilityBooking.objects.select_for_update(),
                    pk=booking.pk,
                    resident=get_resident_profile(user),
                )

                if booking.status != FacilityBooking.Status.PENDING:
                    messages.error(
                        request,
                        "This booking has already been reviewed and cannot be cancelled.",
                    )
                    return redirect(
                        "facilities:booking_detail",
                        booking_id=booking.pk,
                    )

                booking.status = FacilityBooking.Status.CANCELLED
                booking.save(update_fields=["status", "updated_at"])

            messages.success(
                request,
                "Your booking request has been cancelled.",
            )
            return redirect("facilities:dashboard")


    return render(
        request,
        "facilities/booking_detail.html",
        {
            "booking": booking,
            "review_form": review_form,
            "role": role,
        },
    )
