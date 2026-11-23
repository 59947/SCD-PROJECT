
from datetime import date

from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.monitoring_repository import monitoring_repository
from .repositories.group_repository import group_repository
from .repositories.allocation_repository import allocation_repository
from .repositories.supervisor_repository import supervisor_repository


MONITORING_STATUSES = [
    "Not Started",
    "In Progress",
    "Delayed",
    "Completed",
    "On Hold",
]


def get_monitoring_form_data(request):
    try:
        group_id = int(request.POST.get("group_id", ""))
    except (TypeError, ValueError):
        group_id = None

    try:
        progress = int(request.POST.get("progress", "0"))
    except (TypeError, ValueError):
        progress = -1

    return {
        "group_id": group_id,
        "progress": progress,
        "status": request.POST.get("status", "Not Started").strip(),
        "start_date": request.POST.get("start_date", "").strip(),
        "deadline": request.POST.get("deadline", "").strip(),
        "last_update": date.today().isoformat(),
        "milestones": request.POST.get("milestones", "").strip(),
        "notes": request.POST.get("notes", "").strip(),
    }


def validate_monitoring(data, exclude_id=None):
    errors = []

    if data["group_id"] is None:
        errors.append("Please select a project group.")

    elif group_repository.get_by_id(data["group_id"]) is None:
        errors.append("The selected group does not exist.")

    elif monitoring_repository.get_by_group(
        data["group_id"],
        exclude_id=exclude_id
    ):
        errors.append("This group already has a monitoring record.")

    if not isinstance(data["progress"], int) or not 0 <= data["progress"] <= 100:
        errors.append("Progress must be a number between 0 and 100.")

    if data["status"] not in MONITORING_STATUSES:
        errors.append("Please select a valid project status.")

    if not data["start_date"]:
        errors.append("Project start date is required.")
    else:
        try:
            date.fromisoformat(data["start_date"])
        except ValueError:
            errors.append("Please enter a valid start date.")

    if not data["deadline"]:
        errors.append("Project deadline is required.")
    else:
        try:
            date.fromisoformat(data["deadline"])
        except ValueError:
            errors.append("Please enter a valid deadline.")

    if data["start_date"] and data["deadline"]:
        try:
            start = date.fromisoformat(data["start_date"])
            deadline = date.fromisoformat(data["deadline"])

            if deadline < start:
                errors.append("Deadline cannot be earlier than the start date.")
        except ValueError:
            pass

    return errors


def prepare_monitoring(record):
    if record is None:
        return None

    prepared = dict(record)

    group = group_repository.get_by_id(record["group_id"])
    prepared["group"] = group

    allocation = allocation_repository.get_by_group(record["group_id"])
    prepared["allocation"] = allocation

    supervisor = None

    if allocation:
        supervisor = supervisor_repository.get_by_id(
            allocation["supervisor_id"]
        )

    prepared["supervisor"] = supervisor

    return prepared


def get_monitoring_groups():
    available_groups = []

    for group in group_repository.get_all():
        if monitoring_repository.get_by_group(group["id"]) is None:
            available_groups.append(group)

    return available_groups


def manage_monitoring(request):
    all_records = monitoring_repository.get_all()

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    records = []

    for record in all_records:
        prepared = prepare_monitoring(record)
        group = prepared["group"]

        if group is None:
            continue

        if search:
            term = search.casefold()

            searchable = (
                group["group_name"]
                + " "
                + group["group_code"]
                + " "
                + group["project_title"]
            ).casefold()

            if term not in searchable:
                continue

        if status_filter in MONITORING_STATUSES:
            if record["status"] != status_filter:
                continue

        records.append(prepared)

    context = {
        "active_page": "monitoring",
        "records": records,
        "total_projects": len(all_records),
        "in_progress": sum(
            r["status"] == "In Progress" for r in all_records
        ),
        "delayed_projects": sum(
            r["status"] == "Delayed" for r in all_records
        ),
        "completed_projects": sum(
            r["status"] == "Completed" for r in all_records
        ),
        "search": search,
        "status_filter": status_filter,
        "monitoring_statuses": MONITORING_STATUSES,
    }

    return render(
        request,
        "admins/monitoring_list.html",
        context
    )


def add_monitoring(request):
    errors = []

    record = {
        "group_id": None,
        "progress": 0,
        "status": "Not Started",
        "start_date": "",
        "deadline": "",
        "last_update": date.today().isoformat(),
        "milestones": "",
        "notes": "",
    }

    if request.method == "POST":
        record = get_monitoring_form_data(request)
        errors = validate_monitoring(record)

        if not errors:
            monitoring_repository.create(record)
            return redirect("admins:manage_monitoring")

    context = {
        "active_page": "monitoring",
        "page_heading": "Add Project Monitoring",
        "button_text": "Create Monitoring Record",
        "record": record,
        "errors": errors,
        "groups": get_monitoring_groups(),
        "monitoring_statuses": MONITORING_STATUSES,
    }

    return render(
        request,
        "admins/monitoring_form.html",
        context
    )


def monitoring_details(request, record_id):
    record = monitoring_repository.get_by_id(record_id)

    if record is None:
        return redirect("admins:manage_monitoring")

    context = {
        "active_page": "monitoring",
        "record": prepare_monitoring(record),
    }

    return render(
        request,
        "admins/monitoring_details.html",
        context
    )


def edit_monitoring(request, record_id):
    existing_record = monitoring_repository.get_by_id(record_id)

    if existing_record is None:
        return redirect("admins:manage_monitoring")

    errors = []
    record = existing_record

    if request.method == "POST":
        record = get_monitoring_form_data(request)

        errors = validate_monitoring(
            record,
            exclude_id=record_id
        )

        if not errors:
            monitoring_repository.update(record_id, record)
            return redirect(
                "admins:monitoring_details",
                record_id=record_id
            )

    groups = group_repository.get_all()

    context = {
        "active_page": "monitoring",
        "page_heading": "Update Project Monitoring",
        "button_text": "Update Monitoring",
        "record": record,
        "errors": errors,
        "groups": groups,
        "monitoring_statuses": MONITORING_STATUSES,
    }

    return render(
        request,
        "admins/monitoring_form.html",
        context
    )


@require_POST
def delete_monitoring(request, record_id):
    monitoring_repository.delete(record_id)
    return redirect("admins:manage_monitoring")
