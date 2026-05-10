import secrets as std_secrets

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.db.models import Case, IntegerField, When
from django.urls import reverse
from .filters import filter_requests_queryset
from .models import Request
from .forms import RequestForm
from apps.accounts.forms import AdminCreateUserForm
from apps.accounts.models import User

def is_tech_admin(user):
    return user.role in ['tech_admin', 'admin']

def is_admin(user):
    return user.role == 'admin'


_TV_SECRET_MIN_LEN = 12


def _tv_secret_valid(provided):
    """Проверка секрета для TV (GET tv_secret или сегмент URL)."""
    configured = getattr(settings, 'TV_BOARD_SECRET', '').strip()
    if len(configured) < _TV_SECRET_MIN_LEN:
        return False
    p = (provided or '').strip()
    if len(p) != len(configured):
        return False
    return std_secrets.compare_digest(p, configured)


def _tv_board_queryset():
    """Активные заявки для общего экрана (TV): не закрыты, сортировка по срочности."""
    return (
        Request.objects.exclude(status='completed')
        .select_related('created_by', 'assigned_to')
        .annotate(
            _tv_uo=Case(
                When(urgency='critical', then=0),
                When(urgency='high', then=1),
                When(urgency='medium', then=2),
                When(urgency='low', then=3),
                default=4,
                output_field=IntegerField(),
            )
        )
        .order_by('_tv_uo', '-created_at')
    )


@login_required
def create_request(request):
    if request.user.role != 'user':
        messages.error(
            request,
            'Создавать заявки могут только пользователи с ролью «Пользователь».',
        )
        return redirect('my_requests')
    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.created_by = request.user
            req.save()

            messages.success(request, 'Заявка успешно создана!')
            return redirect('my_requests')
    else:
        form = RequestForm()
    return render(request, 'requests/create.html', {'form': form})


@login_required
def my_requests(request):
    if request.user.role == 'user':
        qs = Request.objects.filter(created_by=request.user)
        qs = filter_requests_queryset(
            qs, request.GET, request.user, staff_author=False, tech_assignment=False
        )
    else:
        qs = Request.objects.all()
        qs = filter_requests_queryset(
            qs, request.GET, request.user, staff_author=True, tech_assignment=False
        )
    requests_list = qs.order_by('-created_at')
    return render(
        request,
        'requests/list.html',
        {
            'requests': requests_list,
            'filters_active': bool(request.GET),
            'status_choices': Request.STATUS_CHOICES,
            'urgency_choices': Request.URGENCY_CHOICES,
        },
    )


def requests_api_state(request):
    """JSON для фонового обновления статуса и полей на странице (polling).

    scope=tv доступен без входа при верном tv_secret (как на странице TV).
    Остальные scope требуют авторизации.
    """
    scope = request.GET.get('scope', 'list')
    if scope == 'tv':
        if not _tv_secret_valid(request.GET.get('tv_secret') or ''):
            return JsonResponse({'error': 'forbidden'}, status=403)
        qs = _tv_board_queryset()
    elif scope == 'tech':
        if not request.user.is_authenticated or not is_tech_admin(request.user):
            return JsonResponse({'error': 'forbidden'}, status=403)
        qs = Request.objects.exclude(status='completed')
        qs = filter_requests_queryset(
            qs, request.GET, request.user, staff_author=True, tech_assignment=True
        )
    elif scope == 'list':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'forbidden'}, status=403)
        if request.user.role == 'user':
            qs = Request.objects.filter(created_by=request.user)
            qs = filter_requests_queryset(
                qs, request.GET, request.user, staff_author=False, tech_assignment=False
            )
        else:
            qs = Request.objects.all()
            qs = filter_requests_queryset(
                qs, request.GET, request.user, staff_author=True, tech_assignment=False
            )
    else:
        return JsonResponse({'error': 'bad scope'}, status=400)

    if scope != 'tv':
        qs = qs.order_by('-created_at')
    rows = []
    for r in qs.select_related('created_by', 'assigned_to'):
        if scope == 'tech':
            locked_for_me = (
                request.user.role == 'tech_admin'
                and r.assigned_to_id
                and r.assigned_to_id != request.user.id
            )
        else:
            locked_for_me = False
        rows.append(
            {
                'id': r.pk,
                'owner_number': r.owner_number,
                'status': r.status,
                'status_display': r.get_status_display(),
                'comment': r.comment or '',
                'assigned_to': r.assigned_to.username if r.assigned_to else '',
                'locked_for_me': locked_for_me,
            }
        )
    return JsonResponse({'requests': rows})

def tv_board(request, tv_secret):
    """Экран для телевизора без авторизации: нужен верный секрет в адресе (/requests/tv/<секрет>/)."""
    if not _tv_secret_valid(tv_secret):
        raise Http404()
    configured = settings.TV_BOARD_SECRET.strip()
    requests_list = list(_tv_board_queryset())
    return render(
        request,
        'requests/tv_board.html',
        {
            'requests': requests_list,
            'tv_secret': configured,
        },
    )


@user_passes_test(is_tech_admin)
def tech_dashboard(request):
    qs = Request.objects.exclude(status='completed')
    qs = filter_requests_queryset(
        qs, request.GET, request.user, staff_author=True, tech_assignment=True
    )
    requests_list = qs.order_by('-created_at')
    return render(
        request,
        'requests/tech_dashboard.html',
        {
            'requests': requests_list,
            'filters_active': bool(request.GET),
            'status_choices': Request.STATUS_CHOICES,
            'urgency_choices': Request.URGENCY_CHOICES,
        },
    )


@user_passes_test(is_tech_admin)
@require_POST
def tech_update_request(request):
    req_id = request.POST.get('request_id')
    action = request.POST.get('action')
    comment = request.POST.get('comment', '')
    req = get_object_or_404(Request, pk=req_id)
    if action not in dict(Request.STATUS_CHOICES):
        return JsonResponse({'ok': False, 'error': 'Некорректный статус'}, status=400)
    if request.user.role == 'tech_admin':
        if req.assigned_to_id and req.assigned_to_id != request.user.id:
            return JsonResponse(
                {
                    'ok': False,
                    'error': 'Заявка закреплена за другим тех. администратором.',
                },
                status=403,
            )
    if request.user.role == 'tech_admin':
        req.assigned_to = request.user
    req.status = action
    if comment:
        req.comment = comment
    req.save()
    return JsonResponse(
        {
            'ok': True,
            'status': req.status,
            'status_display': req.get_status_display(),
            'comment': req.comment or '',
            'assigned_to': req.assigned_to.username if req.assigned_to else '',
            'hide': req.status == 'completed',
        }
    )


@user_passes_test(is_admin)
def analytics(request):
    add_user_form = AdminCreateUserForm()
    if request.method == 'POST' and request.POST.get('admin_create_user'):
        add_user_form = AdminCreateUserForm(request.POST)
        if add_user_form.is_valid():
            add_user_form.save()
            messages.success(request, 'Пользователь создан.')
            return redirect('analytics')

    total = Request.objects.count()
    by_status = {status[1]: Request.objects.filter(status=status[0]).count() for status in Request.STATUS_CHOICES}
    by_urgency = {urg[1]: Request.objects.filter(urgency=urg[0]).count() for urg in Request.URGENCY_CHOICES}
    users = User.objects.all().order_by('username')
    uq = (request.GET.get('uq') or '').strip()
    if uq:
        users = users.filter(username__icontains=uq)

    tv_board_url = ''
    tv_secret = getattr(settings, 'TV_BOARD_SECRET', '').strip()
    if len(tv_secret) >= _TV_SECRET_MIN_LEN:
        tv_board_url = request.build_absolute_uri(
            reverse('tv_board', kwargs={'tv_secret': tv_secret})
        )

    return render(request, 'analytics.html', {
        'total': total,
        'by_status': by_status,
        'by_urgency': by_urgency,
        'users': users,
        'add_user_form': add_user_form,
        'user_search_q': uq,
        'user_filters_active': bool(uq),
        'tv_board_url': tv_board_url,
    })