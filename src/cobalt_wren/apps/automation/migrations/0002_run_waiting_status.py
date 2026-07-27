from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("automation", "0001_initial")]

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
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=32,
            ),
        ),
    ]
