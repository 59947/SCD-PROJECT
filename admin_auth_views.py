
from functools import wraps

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.admin_repository import admin_repository


def admin_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("admin_logged_in"):
            messages.warning(request, "Please log in to continue.")
            return redirect("admins:admin_access")

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_access(request):
    if request.session.get("admin_logged_in"):
        return redirect("admins:admin_dashboard")

    if request.method == "POST":
        action = request.POST.get("action", "login").strip().lower()

        # -------------------------
        # ADMIN SIGN UP
        # -------------------------
        if action == "signup":
            name = request.POST.get("name", "").strip()
            email = request.POST.get("email", "").strip().lower()
            password = request.POST.get("password", "")
            confirm_password = request.POST.get("confirm_password", "")

            errors = []

            if not name:
                errors.append("Full name is required.")

            if not email or "@" not in email or "." not in email.split("@")[-1]:
                errors.append("Enter a valid email address.")

            if len(password) < 8:
                errors.append("Password must contain at least 8 characters.")

            if password != confirm_password:
                errors.append("Passwords do not match.")

            if admin_repository.get() is not None:
                errors.append(
                    "An Administrator account already exists. Please log in."
                )

            if errors:
                for error in errors:
                    messages.error(request, error)

                return render(
                    request,
                    "admins/admin_access.html",
                    {
                        "active_tab": "signup",
                        "account_exists": admin_repository.get() is not None,
                        "signup_name": name,
                        "signup_email": email,
                    },
                )

            try:
                admin_repository.create(name, email, password)

                messages.success(
                    request,
                    "Administrator account created successfully. Please log in.",
                )

                return render(
                    request,
                    "admins/admin_access.html",
                    {
                        "active_tab": "login",
                        "account_exists": True,
                        "login_email": email,
                    },
                )

            except ValueError as error:
                messages.error(request, str(error))

                return render(
                    request,
                    "admins/admin_access.html",
                    {
                        "active_tab": "signup",
                        "account_exists": admin_repository.get() is not None,
                        "signup_name": name,
                        "signup_email": email,
                    },
                )

        # -------------------------
        # ADMIN LOGIN
        # -------------------------
        elif action == "login":
            email = request.POST.get("email", "").strip().lower()
            password = request.POST.get("password", "")

            if admin_repository.authenticate(email, password):
                admin = admin_repository.get()

                request.session.cycle_key()
                request.session["admin_logged_in"] = True
                request.session["admin_email"] = email
                request.session["admin_name"] = admin["name"]

                messages.success(request, "Welcome back, Administrator.")

                return redirect("admins:admin_dashboard")

            messages.error(request, "Invalid email address or password.")

            return render(
                request,
                "admins/admin_access.html",
                {
                    "active_tab": "login",
                    "account_exists": admin_repository.get() is not None,
                    "login_email": email,
                },
            )

        else:
            messages.error(request, "Invalid request.")

    return render(
        request,
        "admins/admin_access.html",
        {
            "active_tab": "login",
            "account_exists": admin_repository.get() is not None,
        },
    )


@admin_login_required
def admin_profile(request):
    admin = admin_repository.get()

    if admin is None:
        request.session.flush()
        return redirect("admins:admin_access")

    return render(
        request,
        "admins/admin_profile.html",
        {
            "admin": admin,
            "admin_name": admin["name"],
        },
    )


@admin_login_required
def edit_admin_profile(request):
    admin = admin_repository.get()

    if admin is None:
        request.session.flush()
        return redirect("admins:admin_access")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()

        if not name or not email or "@" not in email:
            messages.error(request, "Enter a valid name and email address.")

        elif admin_repository.update_profile(name, email):
            request.session["admin_email"] = email
            request.session["admin_name"] = name

            messages.success(request, "Your profile has been updated.")
            return redirect("admins:admin_profile")

        else:
            messages.error(request, "Unable to update your profile.")

    return render(
        request,
        "admins/admin_profile_edit.html",
        {"admin": admin},
    )


@admin_login_required
def change_admin_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if len(new_password) < 8:
            messages.error(
                request,
                "New password must contain at least 8 characters.",
            )

        elif new_password != confirm_password:
            messages.error(request, "The new passwords do not match.")

        elif admin_repository.change_password(
            current_password,
            new_password,
        ):
            messages.success(request, "Password changed successfully.")
            return redirect("admins:admin_profile")

        else:
            messages.error(request, "Your current password is incorrect.")

    return render(request, "admins/admin_change_password.html")


@require_POST
def admin_logout(request):
    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect("admins:admin_access")
