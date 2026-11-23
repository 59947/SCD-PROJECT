
from datetime import date as date_type, time as time_type

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Count, Q
from django.db import transaction
from django.utils import timezone

from students.models import (
    ProjectGroup,
    GroupMember,
    Proposal,
    DocumentSubmission,
    ProgressUpdate,
    Meeting,
    Notification,
)

from supervisors.models import SupervisorNotification


User = get_user_model()


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def is_approved_supervisor(user):
    """Check whether the logged-in user is an approved supervisor."""
    return (
        user.is_authenticated
        and getattr(user, 'role', None) == 'supervisor'
        and user.is_approved
    )


supervisor_required = user_passes_test(
    is_approved_supervisor,
    login_url='supervisor_access'
)


def get_unread_notifications_count(supervisor):
    """Return unread notifications for the current supervisor."""
    return SupervisorNotification.objects.filter(
        recipient=supervisor,
        is_read=False
    ).count()


def get_supervisor_notifications(supervisor, limit=8):
    """Return the latest supervisor notifications."""
    return SupervisorNotification.objects.filter(
        recipient=supervisor
    ).order_by('-created_at')[:limit]


def notify_student(
    student_profile,
    title,
    message,
    notification_type='feedback',
    related_url=''
):
    """Create a notification for a student."""
    Notification.objects.create(
        recipient=student_profile,
        title=title,
        message=message,
        notification_type=notification_type,
        related_url=related_url
    )


def parse_meeting_date_time(date_value, time_value):
    """Validate and parse meeting date and time."""
    try:
        parsed_date = date_type.fromisoformat(date_value)
        parsed_time = time_type.fromisoformat(time_value)
    except (ValueError, TypeError):
        return None, None

    now = timezone.localtime()

    if parsed_date < timezone.localdate():
        return None, None

    if parsed_date == now.date() and parsed_time <= now.time().replace(tzinfo=None):
        return None, None

    return parsed_date, parsed_time


def supervisor_page_context(supervisor):
    """Common context used by supervisor pages."""
    return {
        'supervisor': supervisor,
        'unread_notifications_count': get_unread_notifications_count(
            supervisor
        ),
    }


# =====================================================
# SUPERVISOR SIGNUP AND LOGIN
# =====================================================

def supervisor_access(request):

    if request.user.is_authenticated:
        if is_approved_supervisor(request.user):
            return redirect('supervisor_dashboard')

    if request.method == 'POST':

        form_type = request.POST.get('form_type', '').strip()

        # ---------------- SIGNUP ----------------

        if form_type == 'signup':

            first_name = request.POST.get(
                'first_name', ''
            ).strip()

            last_name = request.POST.get(
                'last_name', ''
            ).strip()

            email = request.POST.get(
                'email', ''
            ).strip().lower()

            password = request.POST.get('password', '')
            confirm_password = request.POST.get(
                'confirm_password', ''
            )

            if not all([
                first_name,
                last_name,
                email,
                password,
                confirm_password
            ]):
                messages.error(
                    request,
                    'Please fill in all fields.'
                )
                return redirect('supervisor_access')

            if User.objects.filter(
                email__iexact=email
            ).exists():
                messages.error(
                    request,
                    'This email is already registered.'
                )
                return redirect('supervisor_access')

            if password != confirm_password:
                messages.error(
                    request,
                    'Passwords do not match.'
                )
                return redirect('supervisor_access')

            if len(password) < 8:
                messages.error(
                    request,
                    'Password must contain at least 8 characters.'
                )
                return redirect('supervisor_access')

            if User.objects.filter(
                username__iexact=email
            ).exists():
                messages.error(
                    request,
                    'An account with this username already exists.'
                )
                return redirect('supervisor_access')

            User.objects.create_user(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                role='supervisor',
                is_approved=False
            )

            messages.success(
                request,
                'Your supervisor account has been created. '
                'Please wait for Administrator approval before logging in.'
            )

            return redirect('supervisor_access')

        # ---------------- LOGIN ----------------

        elif form_type == 'login':

            email = request.POST.get(
                'email', ''
            ).strip().lower()

            password = request.POST.get('password', '')

            if not email or not password:
                messages.error(
                    request,
                    'Please enter your email and password.'
                )
                return redirect('supervisor_access')

            supervisor = User.objects.filter(
                email__iexact=email
            ).first()

            if (
                supervisor is None
                or not supervisor.check_password(password)
            ):
                messages.error(
                    request,
                    'Invalid email or password.'
                )
                return redirect('supervisor_access')

            if supervisor.role != 'supervisor':
                messages.error(
                    request,
                    'This account is not a Supervisor account.'
                )
                return redirect('supervisor_access')

            if not supervisor.is_approved:
                messages.warning(
                    request,
                    'Your account is waiting for Administrator approval.'
                )
                return redirect('supervisor_access')

            user = authenticate(
                request,
                username=supervisor.username,
                password=password
            )

            if user is not None and is_approved_supervisor(user):

                login(request, user)

                messages.success(
                    request,
                    'Login successful.'
                )

                return redirect('supervisor_dashboard')

            messages.error(
                request,
                'Unable to log in. Please try again.'
            )

            return redirect('supervisor_access')

        else:
            messages.error(
                request,
                'Invalid form submission.'
            )
            return redirect('supervisor_access')

    return render(
        request,
        'supervisors/supervisor_access.html'
    )


# =====================================================
# SUPERVISOR DASHBOARD
# =====================================================

@supervisor_required
def supervisor_dashboard(request):

    supervisor = request.user
    today = timezone.localdate()

    # ---------------- UPDATE SUPERVISOR PROFILE ----------------

    if (
        request.method == 'POST'
        and request.POST.get('action') == 'update_profile'
    ):

        first_name = request.POST.get(
            'first_name', ''
        ).strip()

        last_name = request.POST.get(
            'last_name', ''
        ).strip()

        email = request.POST.get(
            'email', ''
        ).strip().lower()

        if not first_name or not last_name or not email:

            messages.error(
                request,
                'Please fill in all profile fields.'
            )

        elif User.objects.filter(
            email__iexact=email
        ).exclude(pk=supervisor.pk).exists():

            messages.error(
                request,
                'This email address is already registered.'
            )

        elif User.objects.filter(
            username__iexact=email
        ).exclude(pk=supervisor.pk).exists():

            messages.error(
                request,
                'This email address is already being used as a username.'
            )

        else:

            supervisor.first_name = first_name
            supervisor.last_name = last_name
            supervisor.email = email
            supervisor.username = email

            supervisor.save(
                update_fields=[
                    'first_name',
                    'last_name',
                    'email',
                    'username'
                ]
            )

            messages.success(
                request,
                'Your profile has been updated successfully.'
            )

        return redirect('supervisor_dashboard')

    # ---------------- NOTIFICATIONS ----------------

    supervisor_notifications = get_supervisor_notifications(
        supervisor
    )

    unread_notifications_count = get_unread_notifications_count(
        supervisor
    )

    # ---------------- ASSIGNED GROUPS ----------------

    assigned_groups = (
        ProjectGroup.objects
        .filter(supervisor=supervisor)
        .annotate(
            student_count=Count('members', distinct=True)
        )
        .order_by('-created_at')
    )

    assigned_groups_count = assigned_groups.count()

    # ---------------- TOTAL UNIQUE STUDENTS ----------------

    total_students = (
        GroupMember.objects
        .filter(project_group__supervisor=supervisor)
        .values('student_id')
        .distinct()
        .count()
    )

    # ---------------- APPROVED PROJECTS ----------------

    projects_in_progress = assigned_groups.filter(
        status='approved'
    ).count()

    # ---------------- PENDING PROPOSALS ----------------

    pending_proposals_count = Proposal.objects.filter(
        project_group__supervisor=supervisor,
        status__in=['submitted', 'under_review']
    ).count()

    # ---------------- PENDING DOCUMENTS ----------------

    pending_documents_count = DocumentSubmission.objects.filter(
        project_group__supervisor=supervisor,
        status__in=['pending', 'under_review']
    ).count()

    pending_reviews_count = (
        pending_proposals_count + pending_documents_count
    )

    # ---------------- PENDING MEETINGS ----------------

    pending_meetings_count = Meeting.objects.filter(
        project_group__supervisor=supervisor,
        status='pending'
    ).count()

    # ---------------- UPCOMING MEETINGS ----------------

    upcoming_meetings = (
        Meeting.objects
        .filter(
            project_group__supervisor=supervisor,
            meeting_date__gte=today,
            status__in=['pending', 'accepted', 'rescheduled']
        )
        .select_related('project_group')
        .order_by('meeting_date', 'meeting_time')[:5]
    )

    # ---------------- RECENT ACTIVITIES ----------------

    recent_activities = []

    proposals = (
        Proposal.objects
        .filter(
            project_group__supervisor=supervisor,
            submitted_at__isnull=False
        )
        .select_related(
            'submitted_by__user',
            'project_group'
        )
        .order_by('-submitted_at')[:5]
    )

    for proposal in proposals:

        student = proposal.submitted_by.user
        student_name = student.get_full_name() or student.email

        recent_activities.append({
            'timestamp': proposal.submitted_at,
            'description': (
                f'New proposal submitted by {student_name} '
                f'({proposal.project_group.group_name})'
            ),
            'color': 'blue',
        })

    documents = (
        DocumentSubmission.objects
        .filter(
            project_group__supervisor=supervisor,
            submitted_at__isnull=False
        )
        .select_related(
            'submitted_by__user',
            'project_group'
        )
        .order_by('-submitted_at')[:5]
    )

    for document in documents:

        student = document.submitted_by.user
        student_name = student.get_full_name() or student.email

        recent_activities.append({
            'timestamp': document.submitted_at,
            'description': (
                f'Document uploaded by {student_name} '
                f'({document.project_group.group_name})'
            ),
            'color': 'orange',
        })

    progress_updates = (
        ProgressUpdate.objects
        .filter(
            project_group__supervisor=supervisor
        )
        .select_related(
            'submitted_by__user',
            'project_group'
        )
        .order_by('-submitted_at')[:5]
    )

    for progress in progress_updates:

        student = progress.submitted_by.user
        student_name = student.get_full_name() or student.email

        recent_activities.append({
            'timestamp': progress.submitted_at,
            'description': (
                f'Progress update received from {student_name} '
                f'({progress.project_group.group_name})'
            ),
            'color': 'green',
        })

    recent_activities.sort(
        key=lambda activity: (
            activity['timestamp'] is not None,
            activity['timestamp']
        ),
        reverse=True
    )

    recent_activities = recent_activities[:5]

    # ---------------- PROGRESS UPDATE COUNT ----------------

    total_progress_updates = ProgressUpdate.objects.filter(
        project_group__supervisor=supervisor
    ).count()

    # ---------------- DASHBOARD CONTEXT ----------------

    context = {
        'supervisor': supervisor,

        'assigned_groups': assigned_groups[:5],
        'assigned_groups_count': assigned_groups_count,

        'total_students': total_students,
        'projects_in_progress': projects_in_progress,

        'pending_reviews_count': pending_reviews_count,
        'pending_proposals_count': pending_proposals_count,
        'pending_documents_count': pending_documents_count,

        'pending_meetings_count': pending_meetings_count,

        # ProgressUpdate has no pending/approved status field.
        'total_progress_updates': total_progress_updates,
        'pending_progress_count': 0,

        'upcoming_meetings': upcoming_meetings,
        'recent_activities': recent_activities,

        'supervisor_notifications': supervisor_notifications,
        'unread_notifications_count': unread_notifications_count,
    }

    return render(
        request,
        'supervisors/dashboard.html',
        context
    )


# =====================================================
# ASSIGNED GROUPS
# =====================================================

@supervisor_required
def assigned_groups(request):

    supervisor = request.user

    all_assigned_groups = (
        ProjectGroup.objects
        .filter(supervisor=supervisor)
        .annotate(
            student_count=Count('members', distinct=True)
        )
        .order_by('-created_at')
    )

    # ---------------- SEARCH ----------------

    search_query = request.GET.get(
        'search', ''
    ).strip()

    filtered_groups = all_assigned_groups

    if search_query:
        filtered_groups = filtered_groups.filter(
            Q(group_name__icontains=search_query)
            | Q(project_title__icontains=search_query)
        )

    # ---------------- STATUS FILTER ----------------

    selected_status = request.GET.get(
        'status', ''
    ).strip()

    status_choices = ProjectGroup._meta.get_field(
        'status'
    ).choices

    valid_statuses = [
        value for value, label in status_choices
    ]

    if selected_status in valid_statuses:
        filtered_groups = filtered_groups.filter(
            status=selected_status
        )
    else:
        selected_status = ''

    # ---------------- GROUP PROGRESS ----------------

    assigned_group_rows = []

    for group in filtered_groups:

        latest_progress = (
            ProgressUpdate.objects
            .filter(project_group=group)
            .order_by('-submitted_at', '-id')
            .first()
        )

        progress_percentage = 0

        if latest_progress:
            progress_percentage = (
                latest_progress.progress_percentage or 0
            )

        assigned_group_rows.append({
            'group': group,
            'student_count': group.student_count,
            'progress': progress_percentage,
            'status_label': group.get_status_display(),
        })

    # ---------------- SUMMARY COUNTS ----------------

    total_groups = all_assigned_groups.count()

    total_students = (
        GroupMember.objects
        .filter(project_group__supervisor=supervisor)
        .values('student_id')
        .distinct()
        .count()
    )

    projects_in_progress = all_assigned_groups.filter(
        status='approved'
    ).count()

    context = {
        **supervisor_page_context(supervisor),

        'assigned_group_rows': assigned_group_rows,

        'total_groups': total_groups,
        'total_students': total_students,
        'projects_in_progress': projects_in_progress,

        'search_query': search_query,
        'selected_status': selected_status,
        'status_choices': status_choices,
    }

    return render(
        request,
        'supervisors/assigned_groups.html',
        context
    )


# =====================================================
# PROPOSAL REVIEWS
# =====================================================

@supervisor_required
def proposal_reviews(request):

    supervisor = request.user

    all_supervisor_proposals = (
        Proposal.objects
        .filter(project_group__supervisor=supervisor)
        .select_related(
            'project_group',
            'submitted_by__user',
            'reviewed_by'
        )
    )

    # ---------------- SUBMIT REVIEW ----------------

    if request.method == 'POST':

        proposal_id = request.POST.get(
            'proposal_id', ''
        ).strip()

        recommendation = request.POST.get(
            'recommendation', ''
        ).strip()

        comments = request.POST.get(
            'comments', ''
        ).strip()

        if not proposal_id.isdigit():
            messages.error(
                request,
                'Please select a valid proposal.'
            )
            return redirect('proposal_reviews')

        proposal = get_object_or_404(
            all_supervisor_proposals,
            pk=int(proposal_id)
        )

        status_mapping = {
            'approve': 'approved',
            'revision': 'revision_required',
            'reject': 'rejected',
        }

        if recommendation not in status_mapping:
            messages.error(
                request,
                'Please select a valid recommendation.'
            )
            return redirect(
                f'{request.path}?proposal_id={proposal.pk}'
            )

        if not comments:
            messages.error(
                request,
                'Please enter your review comments.'
            )
            return redirect(
                f'{request.path}?proposal_id={proposal.pk}'
            )

        with transaction.atomic():

            proposal.status = status_mapping[recommendation]
            proposal.feedback = comments
            proposal.reviewed_by = supervisor

            proposal.save(
                update_fields=[
                    'status',
                    'feedback',
                    'reviewed_by',
                    'updated_at'
                ]
            )

            notify_student(
                student_profile=proposal.submitted_by,
                title='Proposal Review Updated',
                message=(
                    f'Your proposal "{proposal.project_title}" '
                    f'has been reviewed. '
                    f'Status: {proposal.get_status_display()}. '
                    f'Feedback: {comments}'
                ),
                notification_type='feedback',
                related_url='/student/proposal-status/'
            )

        messages.success(
            request,
            'Proposal review has been saved successfully.'
        )

        return redirect('proposal_reviews')

    # ---------------- SEARCH ----------------

    proposals = all_supervisor_proposals.order_by(
        '-submitted_at',
        '-created_at'
    )

    search_query = request.GET.get(
        'search', ''
    ).strip()

    if search_query:
        proposals = proposals.filter(
            Q(project_group__group_name__icontains=search_query)
            | Q(project_title__icontains=search_query)
            | Q(submitted_by__user__first_name__icontains=search_query)
            | Q(submitted_by__user__last_name__icontains=search_query)
        )

    # ---------------- STATUS FILTER ----------------

    selected_status = request.GET.get(
        'status', ''
    ).strip()

    valid_statuses = [
        'submitted',
        'under_review',
        'approved',
        'revision_required',
        'rejected',
        'draft',
    ]

    if selected_status in valid_statuses:
        proposals = proposals.filter(
            status=selected_status
        )
    else:
        selected_status = ''

    # ---------------- SUMMARY COUNTS ----------------

    pending_proposals_count = all_supervisor_proposals.filter(
        status__in=['submitted', 'under_review']
    ).count()

    reviewed_proposals_count = all_supervisor_proposals.filter(
        status__in=[
            'approved',
            'revision_required',
            'rejected'
        ]
    ).count()

    revision_proposals_count = all_supervisor_proposals.filter(
        status='revision_required'
    ).count()

    total_groups_count = ProjectGroup.objects.filter(
        supervisor=supervisor
    ).count()

    # ---------------- SELECTED PROPOSAL ----------------

    selected_proposal = None

    selected_proposal_id = request.GET.get(
        'proposal_id', ''
    ).strip()

    if selected_proposal_id:

        if selected_proposal_id.isdigit():
            selected_proposal = proposals.filter(
                pk=int(selected_proposal_id)
            ).first()

    if selected_proposal is None and proposals.exists():
        selected_proposal = proposals.first()

    # ---------------- PAGE CONTEXT ----------------

    context = {
        **supervisor_page_context(supervisor),

        'proposals': proposals,
        'selected_proposal': selected_proposal,

        'pending_proposals_count': pending_proposals_count,
        'reviewed_proposals_count': reviewed_proposals_count,
        'revision_proposals_count': revision_proposals_count,
        'total_groups_count': total_groups_count,

        'search_query': search_query,
        'selected_status': selected_status,
    }

    return render(
        request,
        'supervisors/proposal_reviews.html',
        context
    )


# =====================================================
# STUDENT PROGRESS
# =====================================================

@supervisor_required
def student_progress(request):

    supervisor = request.user

    all_assigned_groups = (
        ProjectGroup.objects
        .filter(supervisor=supervisor)
        .annotate(
            student_count=Count('members', distinct=True)
        )
        .order_by('-created_at')
    )

    # ---------------- GROUP FILTER ----------------

    selected_group_id = request.GET.get(
        'group_id', ''
    ).strip()

    assigned_groups = all_assigned_groups

    if selected_group_id:

        if (
            selected_group_id.isdigit()
            and all_assigned_groups.filter(
                id=int(selected_group_id)
            ).exists()
        ):

            assigned_groups = assigned_groups.filter(
                id=int(selected_group_id)
            )

        else:
            selected_group_id = ''
            assigned_groups = all_assigned_groups

    # ---------------- PROGRESS FOR EACH GROUP ----------------

    group_rows = []
    progress_values = []

    for group in assigned_groups:

        latest_progress = (
            ProgressUpdate.objects
            .filter(project_group=group)
            .select_related('submitted_by__user')
            .order_by('-submitted_at', '-id')
            .first()
        )

        progress_percentage = 0

        if latest_progress:
            progress_percentage = (
                latest_progress.progress_percentage or 0
            )

        progress_values.append(progress_percentage)

        if latest_progress is None:

            progress_status = 'No Update'
            status_class = 'no-update'

        elif progress_percentage < 40:

            progress_status = 'Needs Attention'
            status_class = 'atrisk'

        else:

            progress_status = 'Progress Reported'
            status_class = 'ontrack'

        group_rows.append({
            'group': group,
            'student_count': group.student_count,
            'latest_progress': latest_progress,
            'progress': progress_percentage,
            'progress_status': progress_status,
            'status_class': status_class,
        })

    # ---------------- SUMMARY COUNTS ----------------

    total_groups = len(group_rows)

    average_progress = 0

    if progress_values:
        average_progress = round(
            sum(progress_values) / len(progress_values)
        )

    at_risk_count = sum(
        1
        for row in group_rows
        if (
            row['latest_progress'] is not None
            and row['progress'] < 40
        )
    )

    # ---------------- REAL PROGRESS UPDATES ----------------

    recent_updates = (
        ProgressUpdate.objects
        .filter(project_group__supervisor=supervisor)
        .select_related(
            'project_group',
            'submitted_by__user'
        )
        .order_by('-submitted_at', '-id')
    )

    if selected_group_id:
        recent_updates = recent_updates.filter(
            project_group__id=int(selected_group_id)
        )

    total_updates = recent_updates.count()

    recent_updates = recent_updates[:6]

    context = {
        **supervisor_page_context(supervisor),

        'all_assigned_groups': all_assigned_groups,

        'assigned_groups': assigned_groups,
        'group_rows': group_rows,

        'total_groups': total_groups,
        'average_progress': average_progress,
        'at_risk_count': at_risk_count,
        'total_updates': total_updates,

        'recent_updates': recent_updates,

        'selected_group_id': selected_group_id,
    }

    return render(
        request,
        'supervisors/student_progress.html',
        context
    )


# =====================================================
# DOCUMENT REVIEWS
# =====================================================

@supervisor_required
def document_reviews(request):

    supervisor = request.user

    all_documents = (
        DocumentSubmission.objects
        .filter(project_group__supervisor=supervisor)
        .select_related(
            'project_group',
            'submitted_by__user',
            'reviewed_by'
        )
        .order_by('-submitted_at', '-updated_at', '-id')
    )

    # ---------------- SUBMIT DOCUMENT REVIEW ----------------

    if request.method == 'POST':

        document_id = request.POST.get(
            'document_id', ''
        ).strip()

        recommendation = request.POST.get(
            'recommendation', ''
        ).strip()

        comments = request.POST.get(
            'comments', ''
        ).strip()

        if not document_id.isdigit():
            messages.error(
                request,
                'Please select a valid document.'
            )
            return redirect('document_reviews')

        document = get_object_or_404(
            all_documents,
            pk=int(document_id)
        )

        status_mapping = {
            'approve': 'approved',
            'revision': 'revision_required',
            'reject': 'rejected',
        }

        if recommendation not in status_mapping:
            messages.error(
                request,
                'Please select a valid review decision.'
            )
            return redirect(
                f'{request.path}?document_id={document.pk}'
            )

        if not comments:
            messages.error(
                request,
                'Please enter your review comments.'
            )
            return redirect(
                f'{request.path}?document_id={document.pk}'
            )

        with transaction.atomic():

            document.status = status_mapping[recommendation]
            document.feedback = comments
            document.reviewed_by = supervisor

            document.save(
                update_fields=[
                    'status',
                    'feedback',
                    'reviewed_by',
                    'updated_at'
                ]
            )

            notify_student(
                student_profile=document.submitted_by,
                title='Document Review Updated',
                message=(
                    f'Your {document.get_document_type_display()} '
                    f'has been reviewed. '
                    f'Status: {document.get_status_display()}. '
                    f'Feedback: {comments}'
                ),
                notification_type='feedback',
                related_url='/student/document-submission/'
            )

        messages.success(
            request,
            'Document review has been saved successfully.'
        )

        return redirect(
            f'{request.path}?document_id={document.pk}'
        )

    # ---------------- SUMMARY COUNTS ----------------

    total_documents = all_documents.count()

    reviewed_documents_count = all_documents.filter(
        status__in=[
            'approved',
            'revision_required',
            'rejected'
        ]
    ).count()

    pending_documents_count = all_documents.filter(
        status__in=[
            'pending',
            'under_review'
        ]
    ).count()

    groups_with_documents_count = (
        all_documents
        .values('project_group_id')
        .distinct()
        .count()
    )

    # ---------------- SEARCH ----------------

    documents = all_documents

    search_query = request.GET.get(
        'search', ''
    ).strip()

    if search_query:
        documents = documents.filter(
            Q(project_group__group_name__icontains=search_query)
            | Q(document_type__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(submitted_by__user__first_name__icontains=search_query)
            | Q(submitted_by__user__last_name__icontains=search_query)
        )

    # ---------------- STATUS FILTER ----------------

    selected_status = request.GET.get(
        'status', ''
    ).strip()

    valid_statuses = [
        'pending',
        'under_review',
        'approved',
        'revision_required',
        'rejected'
    ]

    if selected_status in valid_statuses:
        documents = documents.filter(
            status=selected_status
        )
    else:
        selected_status = ''

    # ---------------- SELECTED DOCUMENT ----------------

    selected_document = None

    selected_document_id = request.GET.get(
        'document_id', ''
    ).strip()

    if selected_document_id.isdigit():
        selected_document = documents.filter(
            pk=int(selected_document_id)
        ).first()

    if selected_document is None and documents.exists():
        selected_document = documents.first()

    context = {
        **supervisor_page_context(supervisor),

        'documents': documents,
        'selected_document': selected_document,

        'total_documents': total_documents,
        'reviewed_documents_count': reviewed_documents_count,
        'pending_documents_count': pending_documents_count,
        'groups_with_documents_count': groups_with_documents_count,

        'search_query': search_query,
        'selected_status': selected_status,
    }

    return render(
        request,
        'supervisors/document_reviews.html',
        context
    )


# =====================================================
# GROUP DETAILS
# =====================================================

@supervisor_required
def group_details(request):

    supervisor = request.user

    assigned_groups = (
        ProjectGroup.objects
        .filter(supervisor=supervisor)
        .annotate(
            student_count=Count('members', distinct=True)
        )
        .order_by('-created_at')
    )

    selected_group_id = request.GET.get(
        'group_id', ''
    ).strip()

    selected_group = None
    group_members = []
    latest_progress = None
    proposal = None
    documents = DocumentSubmission.objects.none()

    if selected_group_id:

        if not selected_group_id.isdigit():
            messages.error(
                request,
                'Invalid group selected.'
            )
            return redirect('group_details')

        selected_group = get_object_or_404(
            assigned_groups,
            pk=int(selected_group_id)
        )

        group_members = (
            GroupMember.objects
            .filter(project_group=selected_group)
            .select_related('student__user')
            .order_by(
                'role',
                'student__user__first_name'
            )
        )

        latest_progress = (
            ProgressUpdate.objects
            .filter(project_group=selected_group)
            .select_related('submitted_by__user')
            .order_by('-submitted_at', '-id')
            .first()
        )

        proposal = (
            Proposal.objects
            .filter(project_group=selected_group)
            .select_related(
                'submitted_by__user',
                'reviewed_by'
            )
            .first()
        )

        documents = (
            DocumentSubmission.objects
            .filter(project_group=selected_group)
            .select_related(
                'submitted_by__user',
                'reviewed_by'
            )
            .order_by('-submitted_at', '-id')
        )

    context = {
        **supervisor_page_context(supervisor),

        'assigned_groups': assigned_groups,
        'selected_group': selected_group,
        'group_members': group_members,
        'latest_progress': latest_progress,
        'proposal': proposal,
        'documents': documents,
    }

    return render(
        request,
        'supervisors/group_details.html',
        context
    )


# =====================================================
# FEEDBACK AND COMMENTS
# =====================================================

@supervisor_required
def feedback(request):

    supervisor = request.user

    assigned_groups = (
        ProjectGroup.objects
        .filter(supervisor=supervisor)
        .order_by('group_name')
    )

    proposals = (
        Proposal.objects
        .filter(project_group__supervisor=supervisor)
        .select_related(
            'project_group',
            'submitted_by__user',
            'reviewed_by'
        )
        .order_by('-updated_at', '-id')
    )

    documents = (
        DocumentSubmission.objects
        .filter(project_group__supervisor=supervisor)
        .select_related(
            'project_group',
            'submitted_by__user',
            'reviewed_by'
        )
        .order_by('-updated_at', '-id')
    )

    # ---------------- SAVE NEW FEEDBACK ----------------

    if request.method == 'POST':

        target_type = request.POST.get(
            'target_type', ''
        ).strip()

        target_id = request.POST.get(
            'target_id', ''
        ).strip()

        comments = request.POST.get(
            'comments', ''
        ).strip()

        if not target_id.isdigit():
            messages.error(
                request,
                'Please select a valid proposal or document.'
            )
            return redirect('feedback')

        if not comments:
            messages.error(
                request,
                'Please enter your feedback message.'
            )
            return redirect('feedback')

        if target_type == 'proposal':

            target = get_object_or_404(
                proposals,
                pk=int(target_id)
            )

            with transaction.atomic():

                target.feedback = comments
                target.reviewed_by = supervisor

                target.save(
                    update_fields=[
                        'feedback',
                        'reviewed_by',
                        'updated_at'
                    ]
                )

                notify_student(
                    student_profile=target.submitted_by,
                    title='New Supervisor Feedback',
                    message=(
                        f'Your supervisor has provided feedback '
                        f'on your proposal "{target.project_title}". '
                        f'Feedback: {comments}'
                    ),
                    notification_type='feedback',
                    related_url='/student/proposal-status/'
                )

            messages.success(
                request,
                'Proposal feedback has been saved successfully.'
            )

            return redirect(
                f'/supervisor/feedback/?target_type=proposal&target_id={target.pk}'
            )

        elif target_type == 'document':

            target = get_object_or_404(
                documents,
                pk=int(target_id)
            )

            with transaction.atomic():

                target.feedback = comments
                target.reviewed_by = supervisor

                target.save(
                    update_fields=[
                        'feedback',
                        'reviewed_by',
                        'updated_at'
                    ]
                )

                notify_student(
                    student_profile=target.submitted_by,
                    title='New Supervisor Feedback',
                    message=(
                        f'Your supervisor has provided feedback '
                        f'on your {target.get_document_type_display()}. '
                        f'Feedback: {comments}'
                    ),
                    notification_type='feedback',
                    related_url='/student/document-submission/'
                )

            messages.success(
                request,
                'Document feedback has been saved successfully.'
            )

            return redirect(
                f'/supervisor/feedback/?target_type=document&target_id={target.pk}'
            )

        else:
            messages.error(
                request,
                'Invalid feedback type selected.'
            )
            return redirect('feedback')

    # ---------------- CREATE FEEDBACK RECORDS ----------------

    feedback_records = []

    for proposal in proposals:

        feedback_records.append({
            'id': proposal.id,
            'target_type': 'proposal',
            'target_id': proposal.id,
            'group': proposal.project_group,
            'project_title': proposal.project_title,
            'feedback_type': 'Proposal Review',
            'student': proposal.submitted_by.user,
            'feedback': proposal.feedback,
            'date_given': proposal.updated_at,
            'reviewed_by': proposal.reviewed_by,
            'status': proposal.get_status_display(),
        })

    for document in documents:

        feedback_records.append({
            'id': document.id,
            'target_type': 'document',
            'target_id': document.id,
            'group': document.project_group,
            'project_title': document.project_group.project_title,
            'feedback_type': document.get_document_type_display(),
            'student': document.submitted_by.user,
            'feedback': document.feedback,
            'date_given': document.updated_at,
            'reviewed_by': document.reviewed_by,
            'status': document.get_status_display(),
        })

    feedback_records.sort(
        key=lambda item: (
            item['date_given'] is not None,
            item['date_given']
        ),
        reverse=True
    )

    # ---------------- SUMMARY COUNTS ----------------

    total_feedback = sum(
        1 for item in feedback_records
        if item['feedback']
    )

    pending_actions = sum(
        1 for item in feedback_records
        if not item['feedback']
    )

    resolved_feedback = total_feedback
    total_groups = assigned_groups.count()

    # ---------------- SEARCH ----------------

    search_query = request.GET.get(
        'search', ''
    ).strip()

    filtered_feedback = feedback_records

    if search_query:

        search_lower = search_query.lower()

        filtered_feedback = [
            item for item in filtered_feedback
            if (
                search_lower in (item['group'].group_name or '').lower()
                or search_lower in (item['project_title'] or '').lower()
                or search_lower in (item['student'].first_name or '').lower()
                or search_lower in (item['student'].last_name or '').lower()
                or search_lower in (item['student'].email or '').lower()
            )
        ]

    # ---------------- FEEDBACK TYPE FILTER ----------------

    selected_type = request.GET.get(
        'type', ''
    ).strip()

    if selected_type in ['proposal', 'document']:

        filtered_feedback = [
            item for item in filtered_feedback
            if item['target_type'] == selected_type
        ]

    else:
        selected_type = ''

    # ---------------- SELECTED FEEDBACK ----------------

    selected_feedback = None

    selected_target_type = request.GET.get(
        'target_type', ''
    ).strip()

    selected_target_id = request.GET.get(
        'target_id', ''
    ).strip()

    if (
        selected_target_type in ['proposal', 'document']
        and selected_target_id.isdigit()
    ):

        selected_feedback = next(
            (
                item for item in feedback_records
                if (
                    item['target_type'] == selected_target_type
                    and item['target_id'] == int(selected_target_id)
                )
            ),
            None
        )

    if selected_feedback is None and filtered_feedback:
        selected_feedback = filtered_feedback[0]

    context = {
        **supervisor_page_context(supervisor),

        'assigned_groups': assigned_groups,

        'feedback_records': filtered_feedback,
        'selected_feedback': selected_feedback,

        'total_feedback': total_feedback,
        'pending_actions': pending_actions,
        'resolved_feedback': resolved_feedback,
        'total_groups': total_groups,

        'search_query': search_query,
        'selected_type': selected_type,
    }

    return render(
        request,
        'supervisors/feedback.html',
        context
    )


# =====================================================
# MEETINGS
# =====================================================

@supervisor_required
def meetings(request):

    supervisor = request.user
    today = timezone.localdate()

    all_meetings = (
        Meeting.objects
        .filter(project_group__supervisor=supervisor)
        .select_related(
            'project_group',
            'requested_by__user',
            'supervisor'
        )
        .order_by('-meeting_date', '-meeting_time')
    )

    # ---------------- HANDLE MEETING ACTIONS ----------------

    if request.method == 'POST':

        action = request.POST.get(
            'action', ''
        ).strip()

        # -------- ACCEPT OR REJECT REQUEST --------

        if action in ['accept', 'reject']:

            meeting_id = request.POST.get(
                'meeting_id', ''
            ).strip()

            response_text = request.POST.get(
                'response', ''
            ).strip()

            if not meeting_id.isdigit():
                messages.error(
                    request,
                    'Invalid meeting selected.'
                )
                return redirect('meetings')

            meeting = get_object_or_404(
                all_meetings,
                pk=int(meeting_id)
            )

            if meeting.status != 'pending':
                messages.error(
                    request,
                    'Only pending meeting requests can be accepted or rejected.'
                )
                return redirect(
                    f'{request.path}?meeting_id={meeting.pk}'
                )

            if action == 'accept':

                meeting.status = 'accepted'

                meeting.supervisor_response = (
                    response_text or 'Meeting request accepted.'
                )

                success_message = (
                    'Meeting request accepted successfully.'
                )

            else:

                meeting.status = 'rejected'

                meeting.supervisor_response = (
                    response_text or 'Meeting request rejected.'
                )

                success_message = (
                    'Meeting request rejected successfully.'
                )

            with transaction.atomic():

                meeting.save(
                    update_fields=[
                        'status',
                        'supervisor_response',
                        'updated_at'
                    ]
                )

                notify_student(
                    student_profile=meeting.requested_by,
                    title='Meeting Request Updated',
                    message=(
                        f'Your meeting request for '
                        f'{meeting.project_group.group_name} '
                        f'has been {meeting.get_status_display()}. '
                        f'{meeting.supervisor_response}'
                    ),
                    notification_type='meeting',
                    related_url='/student/meetings/'
                )

            messages.success(request, success_message)

            return redirect(
                f'{request.path}?meeting_id={meeting.pk}'
            )

        # -------- RESCHEDULE MEETING --------

        elif action == 'reschedule':

            meeting_id = request.POST.get(
                'meeting_id', ''
            ).strip()

            new_date = request.POST.get(
                'meeting_date', ''
            ).strip()

            new_time = request.POST.get(
                'meeting_time', ''
            ).strip()

            response_text = request.POST.get(
                'response', ''
            ).strip()

            if not meeting_id.isdigit():
                messages.error(
                    request,
                    'Invalid meeting selected.'
                )
                return redirect('meetings')

            meeting = get_object_or_404(
                all_meetings,
                pk=int(meeting_id)
            )

            if meeting.status == 'rejected':
                messages.error(
                    request,
                    'A rejected meeting cannot be rescheduled.'
                )
                return redirect(
                    f'{request.path}?meeting_id={meeting.pk}'
                )

            parsed_date, parsed_time = parse_meeting_date_time(
                new_date,
                new_time
            )

            if parsed_date is None or parsed_time is None:
                messages.error(
                    request,
                    'Please select a valid future meeting date and time.'
                )
                return redirect(
                    f'{request.path}?meeting_id={meeting.pk}'
                )

            meeting.meeting_date = parsed_date
            meeting.meeting_time = parsed_time
            meeting.status = 'rescheduled'

            meeting.supervisor_response = (
                response_text
                or 'The supervisor has proposed a new meeting time.'
            )

            with transaction.atomic():

                meeting.save(
                    update_fields=[
                        'meeting_date',
                        'meeting_time',
                        'status',
                        'supervisor_response',
                        'updated_at'
                    ]
                )

                notify_student(
                    student_profile=meeting.requested_by,
                    title='Meeting Rescheduled',
                    message=(
                        f'Your meeting for {meeting.project_group.group_name} '
                        f'has been rescheduled to {parsed_date} at {parsed_time}. '
                        f'{meeting.supervisor_response}'
                    ),
                    notification_type='meeting',
                    related_url='/student/meetings/'
                )

            messages.success(
                request,
                'Meeting rescheduled successfully.'
            )

            return redirect(
                f'{request.path}?meeting_id={meeting.pk}'
            )

        # -------- SCHEDULE NEW MEETING --------

        elif action == 'schedule':

            group_id = request.POST.get(
                'group_id', ''
            ).strip()

            meeting_date = request.POST.get(
                'meeting_date', ''
            ).strip()

            meeting_time = request.POST.get(
                'meeting_time', ''
            ).strip()

            meeting_mode = request.POST.get(
                'meeting_mode', ''
            ).strip()

            agenda = request.POST.get(
                'agenda', ''
            ).strip()

            message_text = request.POST.get(
                'message', ''
            ).strip()

            if not group_id.isdigit():
                messages.error(
                    request,
                    'Please select a valid group.'
                )
                return redirect('meetings')

            group = get_object_or_404(
                ProjectGroup,
                pk=int(group_id),
                supervisor=supervisor
            )

            if not all([
                meeting_date,
                meeting_time,
                meeting_mode,
                agenda
            ]):
                messages.error(
                    request,
                    'Please complete all required meeting fields.'
                )
                return redirect('meetings')

            valid_modes = [
                value
                for value, label in Meeting._meta.get_field(
                    'meeting_mode'
                ).choices
            ]

            if meeting_mode not in valid_modes:
                messages.error(
                    request,
                    'Please select a valid meeting mode.'
                )
                return redirect('meetings')

            parsed_date, parsed_time = parse_meeting_date_time(
                meeting_date,
                meeting_time
            )

            if parsed_date is None or parsed_time is None:
                messages.error(
                    request,
                    'Meeting date and time must be in the future.'
                )
                return redirect('meetings')

            # The existing Meeting model requires a StudentProfile
            # in requested_by. Therefore, the group's leader is used.
            leader = group.leader

            with transaction.atomic():

                new_meeting = Meeting.objects.create(
                    project_group=group,
                    requested_by=leader,
                    supervisor=supervisor,
                    meeting_date=parsed_date,
                    meeting_time=parsed_time,
                    meeting_mode=meeting_mode,
                    agenda=agenda,
                    message=message_text,
                    status='accepted',
                    supervisor_response='Meeting scheduled by supervisor.'
                )

                notify_student(
                    student_profile=leader,
                    title='New Meeting Scheduled',
                    message=(
                        f'A meeting has been scheduled for your group '
                        f'{group.group_name} on {parsed_date} at {parsed_time}. '
                        f'Agenda: {agenda}'
                    ),
                    notification_type='meeting',
                    related_url='/student/meetings/'
                )

            messages.success(
                request,
                'Meeting scheduled successfully.'
            )

            return redirect(
                f'{request.path}?meeting_id={new_meeting.pk}'
            )

        else:

            messages.error(
                request,
                'Invalid meeting action.'
            )
            return redirect('meetings')

    # ---------------- SEARCH ----------------

    search_query = request.GET.get(
        'search', ''
    ).strip()

    meetings_queryset = all_meetings

    if search_query:
        meetings_queryset = meetings_queryset.filter(
            Q(project_group__group_name__icontains=search_query)
            | Q(agenda__icontains=search_query)
            | Q(message__icontains=search_query)
            | Q(requested_by__user__first_name__icontains=search_query)
            | Q(requested_by__user__last_name__icontains=search_query)
        )

    # ---------------- STATUS FILTER ----------------

    selected_status = request.GET.get(
        'status', ''
    ).strip()

    if selected_status == 'upcoming':

        meetings_queryset = meetings_queryset.filter(
            meeting_date__gte=today,
            status__in=['accepted', 'rescheduled']
        )

    elif selected_status == 'completed':

        meetings_queryset = meetings_queryset.filter(
            meeting_date__lt=today,
            status__in=['accepted', 'rescheduled']
        )

    elif selected_status in [
        'pending',
        'accepted',
        'rejected',
        'rescheduled'
    ]:

        meetings_queryset = meetings_queryset.filter(
            status=selected_status
        )

    else:
        selected_status = ''

    # ---------------- SUMMARY COUNTS ----------------

    total_meetings = all_meetings.count()

    completed_meetings = all_meetings.filter(
        meeting_date__lt=today,
        status__in=['accepted', 'rescheduled']
    ).count()

    upcoming_meetings = all_meetings.filter(
        meeting_date__gte=today,
        status__in=['accepted', 'rescheduled']
    ).count()

    pending_requests = all_meetings.filter(
        status='pending'
    ).count()

    # ---------------- SELECTED MEETING ----------------

    selected_meeting = None

    selected_meeting_id = request.GET.get(
        'meeting_id', ''
    ).strip()

    if selected_meeting_id.isdigit():

        selected_meeting = all_meetings.filter(
            pk=int(selected_meeting_id)
        ).first()

    if selected_meeting is None and meetings_queryset.exists():
        selected_meeting = meetings_queryset.first()

    # ---------------- ASSIGNED GROUPS ----------------

    assigned_groups = (
        ProjectGroup.objects
        .filter(supervisor=supervisor)
        .order_by('group_name')
    )

    context = {
        **supervisor_page_context(supervisor),

        'meetings': meetings_queryset,
        'selected_meeting': selected_meeting,

        'assigned_groups': assigned_groups,

        'total_meetings': total_meetings,
        'completed_meetings': completed_meetings,
        'upcoming_meetings': upcoming_meetings,
        'pending_requests': pending_requests,

        'search_query': search_query,
        'selected_status': selected_status,
    }

    return render(
        request,
        'supervisors/meetings.html',
        context
    )


# =====================================================
# MARK ONE NOTIFICATION AS READ
# =====================================================

@supervisor_required
@require_POST
def mark_supervisor_notification_read(
    request,
    notification_id
):

    notification = get_object_or_404(
        SupervisorNotification,
        id=notification_id,
        recipient=request.user
    )

    notification.is_read = True

    notification.save(
        update_fields=['is_read']
    )

    destination = notification.related_url

    if destination and url_has_allowed_host_and_scheme(
        url=destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect(destination)

    return redirect('supervisor_dashboard')


# =====================================================
# MARK ALL NOTIFICATIONS AS READ
# =====================================================

@supervisor_required
@require_POST
def mark_all_supervisor_notifications_read(request):

    SupervisorNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True
    )

    messages.success(
        request,
        'All notifications have been marked as read.'
    )

    return redirect('supervisor_dashboard')
