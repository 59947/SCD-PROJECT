
from .notification_factory import NotificationFactory
from .repositories.notification_repository import notification_repository


class NotificationObserver:

    def update(self, event):
        notification_data = NotificationFactory.create(
            title=event["title"],
            message=event["message"],
            notification_type=event.get("type", "general"),
            link=event.get("link"),
        )

        notification_repository.create(notification_data)


class NotificationSubject:

    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event):
        for observer in self._observers:
            observer.update(event)


notification_subject = NotificationSubject()
notification_observer = NotificationObserver()
notification_subject.attach(notification_observer)


def publish_admin_notification(title, message, notification_type="general", link=None):
    notification_subject.notify({
        "title": title,
        "message": message,
        "type": notification_type,
        "link": link,
    })
