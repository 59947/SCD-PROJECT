
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from students.models import (
    Proposal,
    DocumentSubmission,
    ProgressUpdate,
    Meeting,
)

from supervisors.models import SupervisorNotification


def create_supervisor_notification(
    supervisor,
    title,
    message,
    notification_type,
    related_url
):
    """
    Create a notification for the assigned supervisor.
    """

    if supervisor is None:
        return

    if supervisor.role != 'supervisor':
        return

    SupervisorNotification.objects.create(
        recipient=supervisor,
        title=title,
        message=message,
        notification_type=notification_type,
        related_url=related_url
    )


def get_student_name(student_profile):
    """
    Get the student's full name or email.
    """

    student = student_profile.user

    return student.get_full_name().strip() or student.email


# =====================================================
# PROPOSAL: DETECT STATUS CHANGES
# =====================================================

@receiver(pre_save, sender=Proposal)
def remember_previous_proposal_status(sender, instance, **kwargs):

    if instance.pk:
        previous = Proposal.objects.filter(
            pk=instance.pk
        ).values_list('status', flat=True).first()

        instance._previous_status = previous

    else:
        instance._previous_status = None


@receiver(post_save, sender=Proposal)
def notify_supervisor_about_proposal(
    sender,
    instance,
    created,
    **kwargs
):

    previous_status = getattr(
        instance,
        '_previous_status',
        None
    )

    # Notify only when a proposal is newly submitted
    # or changes from another status to submitted.
    if instance.status != 'submitted':
        return

    if not created and previous_status == 'submitted':
        return

    supervisor = instance.project_group.supervisor

    student_name = get_student_name(
        instance.submitted_by
    )

    create_supervisor_notification(
        supervisor=supervisor,
        title='New Proposal Submitted',
        message=(
            f'{student_name} submitted a proposal '
            f'for group {instance.project_group.group_name}.'
        ),
        notification_type='proposal',
        related_url='/supervisor/proposal-reviews/'
    )


# =====================================================
# DOCUMENT: NOTIFY ON NEW SUBMISSION
# =====================================================

@receiver(post_save, sender=DocumentSubmission)
def notify_supervisor_about_document(
    sender,
    instance,
    created,
    **kwargs
):

    if not created:
        return

    supervisor = instance.project_group.supervisor

    student_name = get_student_name(
        instance.submitted_by
    )

    create_supervisor_notification(
        supervisor=supervisor,
        title='New Document Submitted',
        message=(
            f'{student_name} uploaded a '
            f'{instance.get_document_type_display()} '
            f'for group {instance.project_group.group_name}.'
        ),
        notification_type='document',
        related_url='/supervisor/document-reviews/'
    )


# =====================================================
# PROGRESS: NOTIFY ON NEW UPDATE
# =====================================================

@receiver(post_save, sender=ProgressUpdate)
def notify_supervisor_about_progress(
    sender,
    instance,
    created,
    **kwargs
):

    if not created:
        return

    supervisor = instance.project_group.supervisor

    student_name = get_student_name(
        instance.submitted_by
    )

    create_supervisor_notification(
        supervisor=supervisor,
        title='New Progress Update',
        message=(
            f'{student_name} submitted a progress update '
            f'for group {instance.project_group.group_name}.'
        ),
        notification_type='progress',
        related_url='/supervisor/student-progress/'
    )


# =====================================================
# MEETING: NOTIFY ON NEW REQUEST
# =====================================================

@receiver(post_save, sender=Meeting)
def notify_supervisor_about_meeting(
    sender,
    instance,
    created,
    **kwargs
):

    if not created:
        return

    supervisor = instance.supervisor

    student_name = get_student_name(
        instance.requested_by
    )

    create_supervisor_notification(
        supervisor=supervisor,
        title='New Meeting Request',
        message=(
            f'{student_name} requested a meeting '
            f'for group {instance.project_group.group_name}.'
        ),
        notification_type='meeting',
        related_url='/supervisor/meetings/'
    )
