from django.urls import path

from apps.library import views

urlpatterns = [
    path("save/", views.progression_save, name="progression_save"),
    path("<uuid:uuid>/save/", views.progression_update, name="progression_update"),
    path("<uuid:uuid>/", views.progression_detail, name="progression_detail"),
    path("<uuid:uuid>/export.json", views.progression_export, name="progression_export"),
]
