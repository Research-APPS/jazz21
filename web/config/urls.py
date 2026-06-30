from pathlib import Path
from django.urls import path, include, re_path
from django.views.static import serve

SITE_DIR = Path(__file__).resolve().parent.parent.parent / "site"

urlpatterns = [
    path("lydian/", include("apps.lydian.urls")),
    path("", serve, {"document_root": SITE_DIR, "path": "index.html"}),
    re_path(r"^(?P<path>.+)$", serve, {"document_root": SITE_DIR}),
]
