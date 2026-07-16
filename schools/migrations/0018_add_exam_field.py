from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0017_contactmessage_studentmark_exam"),
        ("exams", "0004_initial"),
    ]

    operations = [
        migrations.RunPython(noop, reverse_code=migrations.RunPython.noop),
    ]
