
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .repositories.notification_repository import notification_repository


@require_POST
def mark_notification_read(request, notification_id):
    notification_repository.mark_as_read(notification_id)
    return redirect(request.META.get("HTTP_REFERER", "admins:admin_dashboard"))


@require_POST
def mark_all_notifications_read(request):
    notification_repository.mark_all_as_read()
    return redirect(request.META.get("HTTP_REFERER", "admins:admin_dashboard"))


@require_POST
def delete_notification(request, notification_id):
    notification_repository.delete(notification_id)
    return redirect(request.META.get("HTTP_REFERER", "admins:admin_dashboard"))
