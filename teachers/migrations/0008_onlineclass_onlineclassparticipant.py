from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0003_class_class_master'),
        ('subjects', '0004_alter_subject_code'),
        ('teachers', '0007_remove_teacher_assigned_class_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnlineClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('duration_minutes', models.PositiveIntegerField(blank=True, null=True)),
                ('meeting_link', models.URLField(blank=True, null=True)),
                ('tools', models.CharField(blank=True, default='Screen Share, Chat, Whiteboard', max_length=250)),
                ('status', models.CharField(choices=[('upcoming', 'Upcoming'), ('live', 'Live'), ('finished', 'Finished')], default='upcoming', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('class_obj', models.ForeignKey(on_delete=models.deletion.CASCADE, to='classes.class')),
                ('school', models.ForeignKey(on_delete=models.deletion.CASCADE, to='schools.school')),
                ('stream', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to='classes.stream')),
                ('subject', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to='subjects.subject')),
                ('teacher', models.ForeignKey(on_delete=models.deletion.CASCADE, to='teachers.teacher')),
            ],
            options={
                'ordering': ['-start_time'],
            },
        ),
        migrations.CreateModel(
            name='OnlineClassParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('not_tried', 'Not Tried'), ('joined', 'Joined'), ('failed', 'Failed to Join')], default='not_tried', max_length=20)),
                ('mic_enabled', models.BooleanField(default=False)),
                ('joined_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('online_class', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='participants', to='teachers.onlineclass')),
                ('student', models.ForeignKey(on_delete=models.deletion.CASCADE, to='students.student')),
            ],
            options={
                'unique_together': {('online_class', 'student')},
            },
        ),
    ]
