'''Web UI URL routes.'''

from __future__ import annotations

from django.urls import path

from .views.artifacts import artifact_download_view, artifact_preview_view
from .views.diagnostics import diagnostic_detail_view
from .views.dynamic_actions import dynamic_action_view
from .views.dynamic_pages import dynamic_detail_view, dynamic_form_view, dynamic_list_view
from .views.fragments import dynamic_fragment_view
from .views.integrations import (
    integration_health_detail_view,
    integration_health_list_view,
)
from .views.run_live import run_live_stream_view, run_live_view

urlpatterns = [
    path(
        "ui/integrations/",
        integration_health_list_view,
        name="integration-health-list",
    ),
    path(
        "ui/integrations/<str:integration_id>/",
        integration_health_detail_view,
        name="integration-health-detail",
    ),
    path("ui/diagnostics/<str:model_key>/<int:object_id>/<str:field_name>/", diagnostic_detail_view, name="diagnostic-detail"),
    path("ui/artifacts/<int:object_id>/preview/", artifact_preview_view, name="artifact-preview"),
    path("ui/runs/<int:object_id>/live/", run_live_view, name="run-live"),
    path("ui/runs/<int:object_id>/stream/", run_live_stream_view, name="run-live-stream"),
    path("ui/artifacts/<int:object_id>/download/", artifact_download_view, name="artifact-download"),
    path('ui/<str:model_key>/', dynamic_list_view, name='dynamic-list'),
    path('ui/<str:model_key>/new/', dynamic_form_view, name='dynamic-create'),
    path('ui/<str:model_key>/<int:object_id>/', dynamic_detail_view, name='dynamic-detail'),
    path('ui/<str:model_key>/<int:object_id>/edit/', dynamic_form_view, name='dynamic-edit'),
    path('ui/<str:model_key>/<int:object_id>/actions/<str:action_name>/', dynamic_action_view, name='dynamic-action'),
    path('ui/<str:model_key>/<int:object_id>/fragments/<str:fragment_name>/', dynamic_fragment_view, name='dynamic-fragment'),
]
