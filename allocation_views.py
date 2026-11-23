from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.allocation_repository import allocation_repository
from .repositories.group_repository import group_repository
from .repositories.supervisor_repository import supervisor_repository


ALLOCATION_STATUSES = ["Active", "Completed"]


def get_allocation_form_data(request):
    try:
        group_id = int(request.POST.get("group_id", ""))
    except (TypeError, ValueError):
        group_id = None

    try:
        supervisor_id = int(request.POST.get("supervisor_id", ""))
    except (TypeError, ValueError):
        supervisor_id = None

    return {
        "group_id": group_id,
        "supervisor_id": supervisor_id,
        "allocated_date": request.POST.get("allocated_date", "").strip(),
        "status": request.POST.get("status", "Active").strip(),
        "notes": request.POST.get("notes", "").strip(),
    }


def validate_allocation(data, exclude_id=None):
    errors = []

    group = (
        group_repository.get_by_id(data["group_id"])
        if data["group_id"] is not None else None
    )

    supervisor = (
        supervisor_repository.get_by_id(data["supervisor_id"])
        if data["supervisor_id"] is not None else None
    )

    if group is None:
        errors.append("Please select a valid project group.")

    if supervisor is None:
        errors.append("Please select a valid supervisor.")

    if not data["allocated_date"]:
        errors.append("Allocation date is required.")

    if data["status"] not in ALLOCATION_STATUSES:
        errors.append("Please select a valid allocation status.")

    if group is not None:
        existing = allocation_repository.get_by_group(
            data["group_id"],
            exclude_id=exclude_id
        )
        if existing is not None:
            errors.append(
                "This group already has an allocated supervisor. "
                "Edit its existing allocation instead."
            )

    return errors


def prepare_allocation(allocation):
    if allocation is None:
        return None

    prepared = dict(allocation)
    prepared["group"] = group_repository.get_by_id(
        allocation["group_id"]
    )
    prepared["supervisor"] = supervisor_repository.get_by_id(
        allocation["supervisor_id"]
    )

    return prepared


def manage_allocations(request):
    all_allocations = allocation_repository.get_all()

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    prepared_allocations = [
        prepare_allocation(allocation)
        for allocation in all_allocations
    ]

    allocations = prepared_allocations

    if search:
        term = search.casefold()
        allocations = [
            allocation for allocation in allocations
            if (
                allocation["group"]
                and term in allocation["group"]["group_name"].casefold()
            )
            or (
                allocation["supervisor"]
                and (
                    term in allocation["supervisor"]["name"].casefold()
                    or term in allocation["supervisor"]["employee_id"].casefold()
                )
            )
        ]

    if status_filter in ALLOCATION_STATUSES:
        allocations = [
            allocation for allocation in allocations
            if allocation["status"] == status_filter
        ]

    context = {
        "active_page": "allocation",
        "allocations": allocations,
        "total_allocations": len(all_allocations),
        "active_allocations": sum(
            a["status"] == "Active" for a in all_allocations
        ),
        "completed_allocations": sum(
            a["status"] == "Completed" for a in all_allocations
        ),
        "search": search,
        "status_filter": status_filter,
        "allocation_statuses": ALLOCATION_STATUSES,
    }

    return render(
        request,
        "admins/allocations_list.html",
        context
    )


def add_allocation(request):
    errors = []

    allocation = {
        "group_id": None,
        "supervisor_id": None,
        "allocated_date": "",
        "status": "Active",
        "notes": "",
    }

    if request.method == "POST":
        allocation = get_allocation_form_data(request)
        errors = validate_allocation(allocation)

        if not errors:
            allocation_repository.create(allocation)
            return redirect("admins:manage_allocations")

    context = {
        "active_page": "allocation",
        "page_heading": "Assign Supervisor",
        "button_text": "Assign Supervisor",
        "allocation": allocation,
        "errors": errors,
        "groups": group_repository.get_all(),
        "supervisors": supervisor_repository.get_all(),
        "allocation_statuses": ALLOCATION_STATUSES,
    }

    return render(
        request,
        "admins/allocation_form.html",
        context
    )


def allocation_details(request, allocation_id):
    allocation = allocation_repository.get_by_id(allocation_id)

    if allocation is None:
        return redirect("admins:manage_allocations")

    context = {
        "active_page": "allocation",
        "allocation": prepare_allocation(allocation),
    }

    return render(
        request,
        "admins/allocation_details.html",
        context
    )


def edit_allocation(request, allocation_id):
    existing = allocation_repository.get_by_id(allocation_id)

    if existing is None:
        return redirect("admins:manage_allocations")

    errors = []
    allocation = existing

    if request.method == "POST":
        allocation = get_allocation_form_data(request)
        errors = validate_allocation(
            allocation,
            exclude_id=allocation_id
        )

        if not errors:
            allocation_repository.update(allocation_id, allocation)
            return redirect(
                "admins:allocation_details",
                allocation_id=allocation_id
            )

    context = {
        "active_page": "allocation",
        "page_heading": "Edit Supervisor Allocation",
        "button_text": "Update Allocation",
        "allocation": allocation,
        "errors": errors,
        "groups": group_repository.get_all(),
        "supervisors": supervisor_repository.get_all(),
        "allocation_statuses": ALLOCATION_STATUSES,
    }

    return render(
        request,
        "admins/allocation_form.html",
        context
    )


@require_POST
def delete_allocation(request, allocation_id):
    allocation_repository.delete(allocation_id)
    return redirect("admins:manage_allocations")