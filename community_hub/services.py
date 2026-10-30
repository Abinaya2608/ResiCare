from django.contrib.auth import get_user_model

from .models import AppNotification

User = get_user_model()


def send_notification(
    recipient,
    title,
    message,
    category=AppNotification.Category.GENERAL,
    target_url="",
):
    """Create an in-app notification for one user."""
    if recipient is None or not getattr(recipient, "is_active", False):
        return None

    return AppNotification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        category=category,
        target_url=target_url,
    )


def notify_roles(
    roles,
    title,
    message,
    category=AppNotification.Category.GENERAL,
    target_url="",
):
    """Notify all active users whose role matches one of the supplied roles."""
    if isinstance(roles, str):
        roles = [roles]

    recipients = User.objects.filter(
        is_active=True,
        role__in=roles,
    ).distinct()

    notifications = [
        AppNotification(
            recipient=user,
            title=title,
            message=message,
            category=category,
            target_url=target_url,
        )
        for user in recipients
    ]

    if notifications:
        AppNotification.objects.bulk_create(notifications)

    return len(notifications)