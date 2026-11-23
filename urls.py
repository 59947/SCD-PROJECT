
from django.urls import path
from . import views


urlpatterns = [

    # Supervisor signup and login
    path(
        '',
        views.supervisor_access,
        name='supervisor_access'
    ),

    # Dashboard
    path(
        'dashboard/',
        views.supervisor_dashboard,
        name='supervisor_dashboard'
    ),

    # Supervisor pages
    path(
        'assigned-groups/',
        views.assigned_groups,
        name='assigned_groups'
    ),

    path(
        'proposal-reviews/',
        views.proposal_reviews,
        name='proposal_reviews'
    ),

    path(
        'student-progress/',
        views.student_progress,
        name='student_progress'
    ),

    path(
        'document-reviews/',
        views.document_reviews,
        name='document_reviews'
    ),

    path(
        'group-details/',
        views.group_details,
        name='group_details'
    ),

    path(
        'feedback/',
        views.feedback,
        name='feedback'
    ),

    path(
        'meetings/',
        views.meetings,
        name='meetings'
    ),

    # Notification actions
    path(
        'notifications/read/<int:notification_id>/',
        views.mark_supervisor_notification_read,
        name='mark_supervisor_notification_read'
    ),

    path(
        'notifications/mark-all-read/',
        views.mark_all_supervisor_notifications_read,
        name='mark_all_supervisor_notifications_read'
    ),
]
