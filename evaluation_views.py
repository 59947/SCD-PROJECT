
from datetime import date

from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .repositories.evaluation_repository import evaluation_repository
from .repositories.group_repository import group_repository
from .grading_strategy import grading_calculator


CRITERIA = [
    {
        "key": "problem_definition",
        "label": "Problem Definition and Research",
    },
    {
        "key": "methodology",
        "label": "Methodology and Planning",
    },
    {
        "key": "implementation",
        "label": "Implementation and Technical Work",
    },
    {
        "key": "presentation",
        "label": "Documentation and Presentation",
    },
]

EVALUATION_STATUSES = ["Draft", "Finalized"]


def get_evaluation_form_data(request):
    data = {
        "group_id": None,
        "evaluator": request.POST.get("evaluator", "").strip(),
        "evaluation_date": request.POST.get(
            "evaluation_date", date.today().isoformat()
        ).strip(),
        "comments": request.POST.get("comments", "").strip(),
        "status": request.POST.get("status", "Draft").strip(),
    }

    try:
        data["group_id"] = int(request.POST.get("group_id", ""))
    except (TypeError, ValueError):
        pass

    for criterion in CRITERIA:
        key = criterion["key"]

        try:
            data[key] = int(request.POST.get(key, "0"))
        except (TypeError, ValueError):
            data[key] = -1

    return data


def validate_evaluation(data, exclude_id=None):
    errors = []

    if data["group_id"] is None:
        errors.append("Please select a project group.")
    elif group_repository.get_by_id(data["group_id"]) is None:
        errors.append("The selected project group does not exist.")
    elif evaluation_repository.get_by_group(
        data["group_id"],
        exclude_id=exclude_id,
    ):
        errors.append("This group already has an evaluation record.")

    if not data["evaluator"]:
        errors.append("Evaluator name is required.")

    if not data["evaluation_date"]:
        errors.append("Evaluation date is required.")
    else:
        try:
            date.fromisoformat(data["evaluation_date"])
        except ValueError:
            errors.append("Please enter a valid evaluation date.")

    if data["status"] not in EVALUATION_STATUSES:
        errors.append("Please select a valid evaluation status.")

    for criterion in CRITERIA:
        key = criterion["key"]
        score = data[key]

        if not isinstance(score, int) or not 0 <= score <= 25:
            errors.append(
                f"{criterion['label']} must be between 0 and 25."
            )

    return errors


def prepare_evaluation(record):
    if record is None:
        return None

    prepared = dict(record)
    prepared["group"] = group_repository.get_by_id(record["group_id"])
    return prepared


def get_available_groups(exclude_group_id=None):
    available = []

    for group in group_repository.get_all():
        existing = evaluation_repository.get_by_group(
            group["id"],
            exclude_id=None,
        )

        if existing is None or group["id"] == exclude_group_id:
            available.append(group)

    return available


def save_evaluation(evaluation_id, data):
    scores = {
        criterion["key"]: data[criterion["key"]]
        for criterion in CRITERIA
    }

    grading = grading_calculator.calculate(scores)

    record_data = {
        **data,
        **grading,
    }

    if evaluation_id is None:
        evaluation_repository.create(record_data)
    else:
        evaluation_repository.update(evaluation_id, record_data)


def manage_evaluations(request):
    evaluations = evaluation_repository.get_all()

    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    result_filter = request.GET.get("result", "").strip()

    records = []

    for evaluation in evaluations:
        prepared = prepare_evaluation(evaluation)
        group = prepared["group"]

        if group is None:
            continue

        if search:
            searchable = (
                group["group_name"]
                + " "
                + group["group_code"]
                + " "
                + group["project_title"]
                + " "
                + evaluation["evaluator"]
            ).casefold()

            if search.casefold() not in searchable:
                continue

        if status_filter in EVALUATION_STATUSES:
            if evaluation["status"] != status_filter:
                continue

        if result_filter in ["Pass", "Fail"]:
            if evaluation["result"] != result_filter:
                continue

        records.append(prepared)

    context = {
        "active_page": "evaluations",
        "records": records,
        "total_evaluations": len(evaluations),
        "passed_count": sum(
            item["result"] == "Pass" for item in evaluations
        ),
        "failed_count": sum(
            item["result"] == "Fail" for item in evaluations
        ),
        "draft_count": sum(
            item["status"] == "Draft" for item in evaluations
        ),
        "search": search,
        "status_filter": status_filter,
        "result_filter": result_filter,
        "evaluation_statuses": EVALUATION_STATUSES,
    }

    return render(
        request,
        "admins/evaluations_list.html",
        context,
    )


def add_evaluation(request):
    errors = []

    record = {
        "group_id": None,
        "evaluator": "",
        "evaluation_date": date.today().isoformat(),
        "comments": "",
        "status": "Draft",
        "problem_definition": 0,
        "methodology": 0,
        "implementation": 0,
        "presentation": 0,
    }

    if request.method == "POST":
        record = get_evaluation_form_data(request)
        errors = validate_evaluation(record)

        if not errors:
            save_evaluation(None, record)
            return redirect("admins:manage_evaluations")

    context = {
        "active_page": "evaluations",
        "page_heading": "Add Evaluation",
        "button_text": "Save Evaluation",
        "record": record,
        "errors": errors,
        "groups": get_available_groups(),
        "criteria": CRITERIA,
        "evaluation_statuses": EVALUATION_STATUSES,
    }

    return render(
        request,
        "admins/evaluation_form.html",
        context,
    )


def evaluation_details(request, evaluation_id):
    evaluation = evaluation_repository.get_by_id(evaluation_id)

    if evaluation is None:
        return redirect("admins:manage_evaluations")

    context = {
        "active_page": "evaluations",
        "record": prepare_evaluation(evaluation),
    }

    return render(
        request,
        "admins/evaluation_details.html",
        context,
    )


def edit_evaluation(request, evaluation_id):
    existing = evaluation_repository.get_by_id(evaluation_id)

    if existing is None:
        return redirect("admins:manage_evaluations")

    errors = []
    record = existing

    if request.method == "POST":
        record = get_evaluation_form_data(request)
        errors = validate_evaluation(
            record,
            exclude_id=evaluation_id,
        )

        if not errors:
            save_evaluation(evaluation_id, record)
            return redirect(
                "admins:evaluation_details",
                evaluation_id=evaluation_id,
            )

    context = {
        "active_page": "evaluations",
        "page_heading": "Edit Evaluation",
        "button_text": "Update Evaluation",
        "record": record,
        "errors": errors,
        "groups": get_available_groups(
            exclude_group_id=existing["group_id"]
        ),
        "criteria": CRITERIA,
        "evaluation_statuses": EVALUATION_STATUSES,
    }

    return render(
        request,
        "admins/evaluation_form.html",
        context,
    )


@require_POST
def delete_evaluation(request, evaluation_id):
    evaluation_repository.delete(evaluation_id)
    return redirect("admins:manage_evaluations")
