from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar_app', '0005_assignmentsubmission'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='event_images/'),
        ),
    ]
