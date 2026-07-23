from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("automation", "0003_run_timed_out_status")]
    operations = [
        migrations.AlterModelOptions(
            name="run",
            options={
                "ordering": ["-created_at"],
                "permissions": [("start_run", "Can start run"), ("resume_run", "Can resume run"), ("cancel_run", "Can cancel run"), ("retry_run", "Can retry run")],
            },
        ),
        migrations.CreateModel(
            name="OperationAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_identifier", models.CharField(blank=True, default="", max_length=255)),
                ("action", models.CharField(max_length=100)),
                ("target_type", models.CharField(max_length=100)),
                ("target_id", models.CharField(max_length=100)),
                ("outcome", models.CharField(max_length=32)),
                ("payload_summary", models.JSONField(blank=True, default=dict)),
                ("message", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to="automation.run")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="operationauditlog", index=models.Index(fields=["target_type", "target_id"], name="auto_audit_target_idx")),
        migrations.AddIndex(model_name="operationauditlog", index=models.Index(fields=["action", "outcome"], name="automation_o_action_0e6831_idx")),
    ]
