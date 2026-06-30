from django.urls import path

from apps.library.views import LibraryLoginView, LibraryLogoutView, csrf_token_view, profile

urlpatterns = [
    path("login/", LibraryLoginView.as_view(), name="login"),
    path("logout/", LibraryLogoutView.as_view(), name="logout"),
    path("profile/", profile, name="profile"),
    path("api/csrf/", csrf_token_view, name="api_csrf"),
]
