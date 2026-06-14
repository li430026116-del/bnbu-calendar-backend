# Generated for assignment submissions.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar_app', '0004_sharelink'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='submissions/')),
                ('submitted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='calendar_app.assignment')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_submissions', to='calendar_app.student')),
            ],
            options={
                'db_table': 'assignment_submissions',
                'unique_together': {('assignment', 'student')},
                'indexes': [models.Index(fields=['assignment', 'student'], name='assignment__assignm_2d61f5_idx')],
            },
        ),
    ]
