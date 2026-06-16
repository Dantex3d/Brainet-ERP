from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0008_onlineclass_onlineclassparticipant'),
    ]

    operations = [
        migrations.AddField(
            model_name='onlineclass',
            name='board_notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='onlineclass',
            name='board_attachment',
            field=models.FileField(blank=True, null=True, upload_to='online_class_boards/'),
        ),
    ]
