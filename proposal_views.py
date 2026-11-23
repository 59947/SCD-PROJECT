from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.proposal_repository import proposal_repository
from .repositories.group_repository import group_repository


PROPOSAL_STATUSES = [
    "Pending",
    "Approved",
    "Rejected",
    "Revision Required",
]


def get_proposal_form_data(request):
    try:
        group_id = int(request.POST.get("group_id", ""))
    except (TypeError, ValueError):
        group_id = None

    return {
        "title": request.POST.get("title", "").strip(),
        "reference": request.POST.get("reference", "").strip(),
        "group_id": group_id,
        "submitted_date": request.POST.get("submitted_date", "").strip(),
        "abstract": request.POST.get("abstract", "").strip(),
        "status": request.POST.get("status", "Pending").strip(),
        "admin_comments": request.POST.get("admin_comments", "").strip(),
    }


def prepare_proposal(proposal):
    if proposal is None:
        return None

    prepared = dict(proposal)
    prepared["group"] = group_repository.get_by_id(
        proposal["group_id"]
    )
    return prepared


def validate_proposal(data, exclude_id=None):
    errors = []

    if not data["title"]:
        errors.append("Proposal title is required.")

    if not data["reference"]:
        errors.append("Proposal reference is required.")
    elif proposal_repository.reference_exists(
        data["reference"], exclude_id=exclude_id
    ):
        errors.append("This proposal reference already exists.")

    if not data["submitted_date"]:
        errors.append("Submission date is required.")

    if not data["abstract"]:
        errors.append("Proposal abstract is required.")

    if data["status"] not in PROPOSAL_STATUSES:
        errors.append("Please select a valid proposal status.")

    if data["group_id"] is None:
        errors.append("Please select a group.")
    elif group_repository.get_by_id(data["group_id"]) is None:
        errors.append("The selected group does not exist.")

    return errors


def manage_proposals(request):
    all_proposals = proposal_repository.get_all()

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    proposals = all_proposals

    if search:
        term = search.casefold()
        filtered = []

        for proposal in proposals:
            group = group_repository.get_by_id(proposal["group_id"])
            group_name = group["group_name"] if group else ""

            if (
                term in proposal["title"].casefold()
                or term in proposal["reference"].casefold()
                or term in group_name.casefold()
            ):
                filtered.append(proposal)

        proposals = filtered

    if status_filter in PROPOSAL_STATUSES:
        proposals = [
            proposal for proposal in proposals
            if proposal["status"] == status_filter
        ]

    prepared_proposals = [
        prepare_proposal(proposal) for proposal in proposals
    ]

    context = {
        "active_page": "proposals",
        "proposals": prepared_proposals,
        "total_proposals": len(all_proposals),
        "pending_proposals": sum(
            p["status"] == "Pending" for p in all_proposals
        ),
        "approved_proposals": sum(
            p["status"] == "Approved" for p in all_proposals
        ),
        "rejected_proposals": sum(
            p["status"] == "Rejected" for p in all_proposals
        ),
        "search": search,
        "status_filter": status_filter,
        "proposal_statuses": PROPOSAL_STATUSES,
    }

    return render(
        request,
        "admins/proposals_list.html",
        context
    )


def add_proposal(request):
    errors = []

    proposal = {
        "title": "",
        "reference": "",
        "group_id": None,
        "submitted_date": "",
        "abstract": "",
        "status": "Pending",
        "admin_comments": "",
    }

    if request.method == "POST":
        proposal = get_proposal_form_data(request)
        errors = validate_proposal(proposal)

        if not errors:
            proposal_repository.create(proposal)
            return redirect("admins:manage_proposals")

    context = {
        "active_page": "proposals",
        "page_heading": "Add Proposal",
        "button_text": "Add Proposal",
        "proposal": proposal,
        "errors": errors,
        "groups": group_repository.get_all(),
        "proposal_statuses": PROPOSAL_STATUSES,
    }

    return render(
        request,
        "admins/proposal_form.html",
        context
    )


def proposal_details(request, proposal_id):
    proposal = proposal_repository.get_by_id(proposal_id)

    if proposal is None:
        return redirect("admins:manage_proposals")

    context = {
        "active_page": "proposals",
        "proposal": prepare_proposal(proposal),
        "proposal_statuses": PROPOSAL_STATUSES,
    }

    return render(
        request,
        "admins/proposal_details.html",
        context
    )


def edit_proposal(request, proposal_id):
    existing_proposal = proposal_repository.get_by_id(proposal_id)

    if existing_proposal is None:
        return redirect("admins:manage_proposals")

    errors = []
    proposal = existing_proposal

    if request.method == "POST":
        proposal = get_proposal_form_data(request)
        errors = validate_proposal(
            proposal,
            exclude_id=proposal_id
        )

        if not errors:
            proposal_repository.update(proposal_id, proposal)
            return redirect("admins:proposal_details", proposal_id=proposal_id)

    context = {
        "active_page": "proposals",
        "page_heading": "Edit Proposal",
        "button_text": "Update Proposal",
        "proposal": proposal,
        "errors": errors,
        "groups": group_repository.get_all(),
        "proposal_statuses": PROPOSAL_STATUSES,
    }

    return render(
        request,
        "admins/proposal_form.html",
        context
    )


@require_POST
def update_proposal_decision(request, proposal_id):
    proposal = proposal_repository.get_by_id(proposal_id)

    if proposal is None:
        return redirect("admins:manage_proposals")

    status = request.POST.get("status", "").strip()
    comments = request.POST.get("admin_comments", "").strip()

    if status in PROPOSAL_STATUSES:
        proposal_repository.update_decision(
            proposal_id,
            status,
            comments
        )

    return redirect(
        "admins:proposal_details",
        proposal_id=proposal_id
    )


@require_POST
def delete_proposal(request, proposal_id):
    proposal_repository.delete(proposal_id)
    return redirect("admins:manage_proposals")