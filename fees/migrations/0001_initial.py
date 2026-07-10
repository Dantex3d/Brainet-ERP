# Generated migration for fees app models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('schools', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FeeStructure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='School Fees Structure', max_length=180)),
                ('term', models.CharField(blank=True, max_length=100)),
                ('components', models.TextField(blank=True, help_text='Enter one component per line such as Tuition: 15000')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_structures', to='schools.school')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FeeInvoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payer_name', models.CharField(blank=True, max_length=200)),
                ('invoice_number', models.CharField(editable=False, max_length=40, unique=True)),
                ('description', models.TextField(blank=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('due_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('payment_method', models.CharField(choices=[('bank', 'Bank Transfer'), ('mpesa', 'M-Pesa'), ('cash', 'Cash'), ('other', 'Other')], default='mpesa', max_length=20)),
                ('payment_reference', models.CharField(blank=True, max_length=120)),
                ('paid', models.BooleanField(default=False)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_fee_invoices', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_invoices', to='schools.school')),
                ('structure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='fees.feestructure')),
            ],
            options={
                'ordering': ['-generated_at'],
            },
        ),
    ]
