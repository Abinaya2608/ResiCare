
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    """Display the dashboard for the authenticated user."""
    user = request.user

    context = {
        "user": user,
        "role": user.role,
    }

    return render(request, "dashboard.html", context)
