from django.db import models
from django.db.models import Max, Q
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.accounts.models import User


def _reset_sqlite_request_sequence_if_empty():
    """После удаления всех заявок следующий id снова начинается с 1 (только SQLite)."""
    if Request.objects.exists():
        return
    from django.db import connection

    if connection.vendor != 'sqlite':
        return
    table = Request._meta.db_table
    if not table.isidentifier():
        return
    # Значение в sqlite_sequence.name — строка; без плейсхолдеров: иначе при DEBUG ломается last_executed_query (sql % params) на Python 3.14.
    literal = "'" + table.replace("'", "''") + "'"
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = " + literal)


class RequestQuerySet(models.QuerySet):
    def delete(self):
        result = super().delete()
        _reset_sqlite_request_sequence_if_empty()
        return result


class RequestManager(models.Manager.from_queryset(RequestQuerySet)):
    pass


class Request(models.Model):
    URGENCY_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
        ('critical', 'Критичная'),
    ]
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('waiting', 'Ожидание'),
        ('completed', 'Готово'),
    ]

    owner_number = models.PositiveIntegerField(
        default=1,
        editable=False,
        verbose_name="Номер у автора",
        help_text="Порядковый номер заявки у пользователя, который её создал",
    )
    title = models.CharField(max_length=200, verbose_name="Название заявки")
    description = models.TextField(verbose_name="Подробности")
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_requests')
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests',
        limit_choices_to=Q(role__in=['tech_admin', 'admin']),
    )
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RequestManager()

    def save(self, *args, **kwargs):
        if self._state.adding and self.created_by_id:
            nxt = (
                Request.objects.filter(created_by_id=self.created_by_id).aggregate(
                    m=Max("owner_number")
                )["m"]
                or 0
            ) + 1
            self.owner_number = nxt
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


@receiver(post_delete, sender=Request)
def _request_post_delete_reset_sequence(sender, instance, **kwargs):
    _reset_sqlite_request_sequence_if_empty()
