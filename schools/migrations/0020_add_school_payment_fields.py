from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0019_remove_term_closing_datetime_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='bank_name',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='school',
            name='account_number',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
