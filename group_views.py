
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.group_repository import group_repository
from .repositories.student_repository import student_repository


GROUP_STATUSES = [
    "Planning",
    "In Progress",
    "Completed",
    "On Hold",
]


def get_group_students(student_ids):
    """Return existing student records for the supplied IDs."""
    students = []

    for student_id in student_ids:
        student = student_repository.get_by_id(student_id)
        if student is not None:
            students.append(student)

    return students


def prepare_group(group):
    """Add student records and leader information for templates."""
    if group is None:
        return None

    prepared = dict(group)
    prepared["students"] = get_group_students(group["student_ids"])

    leader = student_repository.get_by_id(group["leader_id"])
    prepared["leader"] = leader

    return prepared


def get_available_students(exclude_group_id=None, selected_ids=None):
    """List students who are not assigned to another group."""
    selected_ids = selected_ids or []
    available = []

    for student in student_repository.get_all():
        student_id = student["id"]

        if (
            not group_repository.student_is_assigned(
                student_id,
                exclude_group_id=exclude_group_id
            )
            or student_id in selected_ids
        ):
            available.append(student)

    return available


def get_group_form_data(request):
    student_ids = []

    for value in request.POST.getlist("student_ids"):
        try:
            student_id = int(value)
        except (TypeError, ValueError):
            continue

        if student_id not in student_ids:
            student_ids.append(student_id)

    try:
        leader_id = int(request.POST.get("leader_id", ""))
    except (TypeError, ValueError):
        leader_id = None

    return {
        "group_name": request.POST.get("group_name", "").strip(),
        "group_code": request.POST.get("group_code", "").strip(),
        "project_title": request.POST.get("project_title", "").strip(),
        "academic_year": request.POST.get("academic_year", "").strip(),
        "description": request.POST.get("description", "").strip(),
        "leader_id": leader_id,
        "student_ids": student_ids,
        "status": request.POST.get("status", "Planning").strip(),
    }


def validate_group(data, exclude_id=None):
    errors = []

    if not data["group_name"]:
        errors.append("Group name is required.")

    if not data["group_code"]:
        errors.append("Group code is required.")
    elif group_repository.group_code_exists(
        data["group_code"],
        exclude_id
    ):
        errors.append("This group code already exists.")

    if not data["project_title"]:
        errors.append("Project title is required.")

    if not data["academic_year"]:
        errors.append("Academic year is required.")

    if data["status"] not in GROUP_STATUSES:
        errors.append("Please select a valid project status.")

    if not data["student_ids"]:
        errors.append("Select at least one student for this group.")

    existing_student_ids = {
        student["id"] for student in student_repository.get_all()
    }

    for student_id in data["student_ids"]:
        if student_id not in existing_student_ids:
            errors.append(
                "One or more selected students do not exist."
            )
            break

    for student_id in data["student_ids"]:
        if group_repository.student_is_assigned(
            student_id,
            exclude_group_id=exclude_id
        ):
            errors.append(
                "One or more selected students already belong to another group."
            )
            break

    if data["leader_id"] is None:
        errors.append("Please select a group leader.")
    elif data["leader_id"] not in data["student_ids"]:
        errors.append("The group leader must be one of the selected members.")
    elif data["leader_id"] not in existing_student_ids:
        errors.append("The selected group leader does not exist.")

    return errors


def manage_groups(request):
    all_groups = group_repository.get_all()

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    groups = all_groups

    if search:
        term = search.casefold()
        groups = [
            group for group in groups
            if term in group["group_name"].casefold()
            or term in group["group_code"].casefold()
            or term in group["project_title"].casefold()
        ]

    if status_filter in GROUP_STATUSES:
        groups = [
            group for group in groups
            if group["status"] == status_filter
        ]

    prepared_groups = []

    for group in groups:
        prepared = prepare_group(group)
        prepared["member_count"] = len(prepared["students"])
        prepared_groups.append(prepared)

    context = {
        "active_page": "groups",
        "groups": prepared_groups,
        "total_groups": len(all_groups),
        "planning_groups": sum(
            group["status"] == "Planning" for group in all_groups
        ),
        "active_groups": sum(
            group["status"] == "In Progress" for group in all_groups
        ),
        "completed_groups": sum(
            group["status"] == "Completed" for group in all_groups
        ),
        "search": search,
        "status_filter": status_filter,
        "group_statuses": GROUP_STATUSES,
    }

    return render(request, "admins/groups_list.html", context)


def add_group(request):
    errors = []
    group = {
        "group_name": "",
        "group_code": "",
        "project_title": "",
        "academic_year": "",
        "description": "",
        "leader_id": None,
        "student_ids": [],
        "status": "Planning",
    }

    if request.method == "POST":
        group = get_group_form_data(request)
        errors = validate_group(group)

        if not errors:
            group_repository.create(group)
            return redirect("admins:manage_groups")

    context = {
        "active_page": "groups",
        "page_heading": "Create Group",
        "button_text": "Create Group",
        "group": group,
        "errors": errors,
        "students": get_available_students(
            selected_ids=group["student_ids"]
        ),
        "group_statuses": GROUP_STATUSES,
    }

    return render(request, "admins/group_form.html", context)


def group_details(request, group_id):
    group = group_repository.get_by_id(group_id)

    if group is None:
        return redirect("admins:manage_groups")

    context = {
        "active_page": "groups",
        "group": prepare_group(group),
    }

    return render(request, "admins/group_details.html", context)


def edit_group(request, group_id):
    existing_group = group_repository.get_by_id(group_id)

    if existing_group is None:
        return redirect("admins:manage_groups")

    errors = []
    group = existing_group

    if request.method == "POST":
        group = get_group_form_data(request)
        errors = validate_group(group, exclude_id=group_id)

        if not errors:
            group_repository.update(group_id, group)
            return redirect("admins:manage_groups")

    context = {
        "active_page": "groups",
        "page_heading": "Edit Group",
        "button_text": "Update Group",
        "group": group,
        "errors": errors,
        "students": get_available_students(
            exclude_group_id=group_id,
            selected_ids=group["student_ids"]
        ),
        "group_statuses": GROUP_STATUSES,
    }

    return render(request, "admins/group_form.html", context)


@require_POST
def delete_group(request, group_id):
    group_repository.delete(group_id)
    return redirect("admins:manage_groups")
