
from django.db import models
from django.conf import settings


class SupervisorNotification(models.Model):

    NOTIFICATION_TYPE_CHOICES = [
        ('proposal', 'New Proposal'),
        ('document', 'New Document'),
        ('progress', 'Progress Update'),
        ('meeting', 'Meeting Request'),
        ('general', 'General Notification'),
    ]

    # Supervisor who receives the notification
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='supervisor_notifications',
        limit_choices_to={'role': 'supervisor'}
    )

    # Notification details
    title = models.CharField(max_length=200)

    message = models.TextField()

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        default='general'
    )

    # Optional link to the relevant page
    related_url = models.CharField(
        max_length=255,
        blank=True
    )

    # Read/unread status
    is_read = models.BooleanField(default=False)

    # Notification creation date
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.recipient}"
