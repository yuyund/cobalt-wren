from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("automation", "0002_run_waiting_status")]

    operations = [
        migrations.AlterField(
            model_name="run",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("running", "Running"),
                    ("waiting", "Waiting"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                    ("timed_out", "Timed out"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=32,
            ),
        ),
    ]
