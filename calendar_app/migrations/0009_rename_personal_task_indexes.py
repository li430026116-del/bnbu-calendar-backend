from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_app", "0008_personaltask"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="personaltask",
            old_name="personal_ta_owner_i_4f3f8c_idx",
            new_name="personal_ta_owner_i_19b6f2_idx",
        ),
        migrations.RenameIndex(
            model_name="personaltask",
            old_name="personal_ta_due_at_7f4f55_idx",
            new_name="personal_ta_due_at_ecb28a_idx",
        ),
    ]
