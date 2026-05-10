from django.db import migrations, models


def backfill_owner_numbers(apps, schema_editor):
    Request = apps.get_model("requests", "Request")
    user_ids = Request.objects.values_list("created_by_id", flat=True).distinct()
    for uid in user_ids:
        qs = Request.objects.filter(created_by_id=uid).order_by("created_at", "pk")
        for n, row in enumerate(qs, start=1):
            Request.objects.filter(pk=row.pk).update(owner_number=n)


class Migration(migrations.Migration):

    dependencies = [
        ("requests", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="request",
            name="owner_number",
            field=models.PositiveIntegerField(
                default=1,
                editable=False,
                verbose_name="Номер у автора",
            ),
        ),
        migrations.RunPython(backfill_owner_numbers, migrations.RunPython.noop),
    ]
