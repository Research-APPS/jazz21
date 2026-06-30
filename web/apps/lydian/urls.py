from django.urls import path
from . import views

urlpatterns = [
    path("", views.explorer, name="lydian-explorer"),
    path("api/system/", views.api_system, name="lydian-api-system"),
]
