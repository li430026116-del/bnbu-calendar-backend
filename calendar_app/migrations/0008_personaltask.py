from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('calendar_app', '0007_rename_assignment__assignm_2d61f5_idx_assignment__assignm_c9693f_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('due_at', models.DateTimeField()),
                ('priority', models.CharField(choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium', max_length=10)),
                ('is_completed', models.BooleanField(default=False)),
                ('share_token', models.CharField(blank=True, db_index=True, max_length=32, null=True, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='personal_tasks', to=settings.AUTH_USER_MODEL)),
                ('source_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='imported_tasks', to='calendar_app.personaltask')),
            ],
            options={
                'db_table': 'personal_tasks',
            },
        ),
        migrations.AddIndex(
            model_name='personaltask',
            index=models.Index(fields=['owner', 'due_at'], name='personal_ta_owner_i_4f3f8c_idx'),
        ),
        migrations.AddIndex(
            model_name='personaltask',
            index=models.Index(fields=['due_at'], name='personal_ta_due_at_7f4f55_idx'),
        ),
    ]
