
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import ResidentProfileForm
from .models import ResidentProfile


@login_required
def my_profile(request):
    if request.user.role != request.user.Role.RESIDENT:
        raise PermissionDenied(
            "Only residents can access the resident profile page."
        )

    profile = ResidentProfile.objects.filter(
        user=request.user
    ).select_related("apartment").first()

    if profile is None:
        messages.info(
            request,
            "Your resident profile has not been created yet. "
            "Please contact residential management.",
        )
        return redirect("dashboard")

    if request.method == "POST":
        form = ResidentProfileForm(request.POST, instance=profile)

        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was updated successfully.")
            return redirect("residents:my_profile")
    else:
        form = ResidentProfileForm(instance=profile)

    context = {
        "profile": profile,
        "form": form,
    }
    
    return render(request, "residents/my_profile.html", context)
