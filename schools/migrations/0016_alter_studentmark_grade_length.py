from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0015_term_opening_closing_datetime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentmark',
            name='grade',
            field=models.CharField(max_length=100, blank=True),
        ),
    ]
