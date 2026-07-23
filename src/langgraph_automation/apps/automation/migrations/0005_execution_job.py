from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("automation", "0004_operation_audit_and_run_permissions")]
    operations = [
        migrations.CreateModel(
            name="ExecutionJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(choices=[("start", "Start"), ("resume", "Resume"), ("retry", "Retry")], max_length=16)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("claimed", "Claimed"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="queued", max_length=16)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("checkpoint_id", models.CharField(blank=True, default="", max_length=255)),
                ("worker_id", models.CharField(blank=True, default="", max_length=255)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("available_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("heartbeat_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="execution_jobs", to="automation.run")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="executionjob", index=models.Index(fields=["status", "available_at"], name="automation_e_status_70f3cf_idx")),
        migrations.AddIndex(model_name="executionjob", index=models.Index(fields=["worker_id", "status"], name="auto_job_worker_status_idx")),
        migrations.AddConstraint(model_name="executionjob", constraint=models.UniqueConstraint(condition=models.Q(("status__in", ["queued", "claimed"])), fields=("run",), name="one_active_execution_job_per_run")),
    ]
