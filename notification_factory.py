
class NotificationFactory:
    """
    Factory Pattern:
    Creates notification objects in a consistent format
    for Admin, Students, and Supervisors.
    """

    @staticmethod
    def create(
        title,
        message,
        notification_type="general",
        link=None
    ):
        """
        Creates and returns a notification dictionary.

        Args:
            title: Notification heading.
            message: Notification description.
            notification_type: Type of notification.
            link: Optional URL related to the notification.

        Returns:
            Dictionary containing notification information.
        """

        if not title or not str(title).strip():
            raise ValueError("Notification title cannot be empty.")

        if not message or not str(message).strip():
            raise ValueError("Notification message cannot be empty.")

        allowed_types = [
            "general",
            "proposal",
            "student",
            "supervisor",
            "group",
            "allocation",
            "monitoring",
            "evaluation",
            "system"
        ]

        if notification_type not in allowed_types:
            notification_type = "general"

        notification = {
            "title": str(title).strip(),
            "message": str(message).strip(),
            "type": notification_type,
            "link": link
        }

        return notification
