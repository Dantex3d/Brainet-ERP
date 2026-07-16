from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0020_add_school_payment_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ErrorReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(blank=True, max_length=500, null=True)),
                ('method', models.CharField(blank=True, max_length=10, null=True)),
                ('exception_type', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('traceback', models.TextField(blank=True, null=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('school', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='error_reports', to='schools.school')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='error_reports', to='users.customuser')),
            ],
        ),
    ]
