'''Web UI URL routes.''' 

from __future__ import annotations

from django.urls import path

from .views.dynamic_actions import dynamic_action_view
from .views.dynamic_pages import dynamic_detail_view, dynamic_form_view, dynamic_list_view
from .views.fragments import dynamic_fragment_view

urlpatterns = [
    path('ui/<str:model_key>/', dynamic_list_view, name='dynamic-list'),
    path('ui/<str:model_key>/new/', dynamic_form_view, name='dynamic-create'),
    path('ui/<str:model_key>/<int:object_id>/', dynamic_detail_view, name='dynamic-detail'),
    path('ui/<str:model_key>/<int:object_id>/edit/', dynamic_form_view, name='dynamic-edit'),
    path('ui/<str:model_key>/<int:object_id>/actions/<str:action_name>/', dynamic_action_view, name='dynamic-action'),
    path('ui/<str:model_key>/<int:object_id>/fragments/<str:fragment_name>/', dynamic_fragment_view, name='dynamic-fragment'),
]
