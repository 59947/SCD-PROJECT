
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.supervisor_repository import supervisor_repository


def get_supervisor_form_data(request):
    return {
        "name": request.POST.get("name", "").strip(),
        "employee_id": request.POST.get("employee_id", "").strip(),
        "email": request.POST.get("email", "").strip().lower(),
        "department": request.POST.get("department", "").strip(),
        "specialization": request.POST.get("specialization", "").strip(),
        "contact_number": request.POST.get("contact_number", "").strip(),
        "status": request.POST.get("status", "Active").strip(),
    }


def validate_supervisor(data, exclude_id=None):
    errors = []

    required_fields = {
        "name": "Full name",
        "employee_id": "Employee ID",
        "email": "Email address",
        "department": "Department",
        "specialization": "Specialization",
        "contact_number": "Contact number",
    }

    for field, label in required_fields.items():
        if not data[field]:
            errors.append(f"{label} is required.")

    if data["email"]:
        if "@" not in data["email"] or "." not in data["email"].split("@")[-1]:
            errors.append("Enter a valid email address.")

    if data["status"] not in ["Active", "Inactive"]:
        errors.append("Select a valid supervisor status.")

    if data["employee_id"] and supervisor_repository.employee_id_exists(
        data["employee_id"], exclude_id
    ):
        errors.append("This Employee ID already exists.")

    if data["email"] and supervisor_repository.email_exists(
        data["email"], exclude_id
    ):
        errors.append("This email address already exists.")

    return errors


def manage_supervisors(request):
    all_supervisors = supervisor_repository.get_all()

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    supervisors = all_supervisors

    if search:
        term = search.casefold()
        supervisors = [
            supervisor for supervisor in supervisors
            if term in supervisor["name"].casefold()
            or term in supervisor["employee_id"].casefold()
            or term in supervisor["email"].casefold()
            or term in supervisor["department"].casefold()
        ]

    if status_filter in ["Active", "Inactive"]:
        supervisors = [
            supervisor for supervisor in supervisors
            if supervisor["status"] == status_filter
        ]

    context = {
        "active_page": "supervisors",
        "supervisors": supervisors,
        "total_supervisors": len(all_supervisors),
        "active_supervisors": sum(
            s["status"] == "Active" for s in all_supervisors
        ),
        "inactive_supervisors": sum(
            s["status"] == "Inactive" for s in all_supervisors
        ),
        "search": search,
        "status_filter": status_filter,
    }

    return render(request, "admins/supervisors_list.html", context)


def add_supervisor(request):
    errors = []
    supervisor = {}

    if request.method == "POST":
        supervisor = get_supervisor_form_data(request)
        errors = validate_supervisor(supervisor)

        if not errors:
            supervisor_repository.create(supervisor)
            return redirect("admins:manage_supervisors")

    context = {
        "active_page": "supervisors",
        "page_heading": "Add Supervisor",
        "button_text": "Save Supervisor",
        "supervisor": supervisor,
        "errors": errors,
    }

    return render(request, "admins/supervisor_form.html", context)


def supervisor_details(request, supervisor_id):
    supervisor = supervisor_repository.get_by_id(supervisor_id)

    if supervisor is None:
        return redirect("admins:manage_supervisors")

    return render(
        request,
        "admins/supervisor_details.html",
        {
            "active_page": "supervisors",
            "supervisor": supervisor,
        },
    )


def edit_supervisor(request, supervisor_id):
    supervisor = supervisor_repository.get_by_id(supervisor_id)

    if supervisor is None:
        return redirect("admins:manage_supervisors")

    errors = []

    if request.method == "POST":
        updated_data = get_supervisor_form_data(request)
        errors = validate_supervisor(updated_data, exclude_id=supervisor_id)

        if not errors:
            supervisor_repository.update(supervisor_id, updated_data)
            return redirect("admins:manage_supervisors")

        supervisor = {**supervisor, **updated_data}

    return render(
        request,
        "admins/supervisor_form.html",
        {
            "active_page": "supervisors",
            "page_heading": "Edit Supervisor",
            "button_text": "Update Supervisor",
            "supervisor": supervisor,
            "errors": errors,
        },
    )


@require_POST
def delete_supervisor(request, supervisor_id):
    supervisor_repository.delete(supervisor_id)
    return redirect("admins:manage_supervisors")
