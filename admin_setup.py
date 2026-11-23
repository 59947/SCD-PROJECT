
from .repositories.admin_repository import admin_repository


def create_initial_admin():
    if admin_repository.get() is None:
        admin_repository.create(
            name="Administrator",
            email="admin@example.com",
            password="Admin@123"
        )
