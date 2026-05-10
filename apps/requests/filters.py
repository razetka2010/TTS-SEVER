from django.db.models import Q

from .models import Request


def filter_requests_queryset(qs, get_params, user, *, staff_author=False, tech_assignment=False):
    """Фильтрация списка заявок по GET-параметрам."""
    q = (get_params.get("q") or "").strip()
    status = get_params.get("status") or ""
    urgency = get_params.get("urgency") or ""
    author = (get_params.get("author") or "").strip()
    assignment = get_params.get("assignment") or ""

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if status in dict(Request.STATUS_CHOICES):
        qs = qs.filter(status=status)
    if urgency in dict(Request.URGENCY_CHOICES):
        qs = qs.filter(urgency=urgency)
    if staff_author and author:
        qs = qs.filter(created_by__username__icontains=author)
    if tech_assignment:
        if assignment == "unassigned":
            qs = qs.filter(assigned_to__isnull=True)
        elif assignment == "mine":
            qs = qs.filter(assigned_to=user)
    return qs
