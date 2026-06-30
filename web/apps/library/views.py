import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.library.models import Progression
from apps.library.services import build_progression_payload


@require_GET
def csrf_token_view(request):
    from django.middleware.csrf import get_token

    return JsonResponse({
        "csrfToken": get_token(request),
        "authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else None,
    })


class LibraryLoginView(LoginView):
    template_name = "library/login.html"


class LibraryLogoutView(LogoutView):
    next_page = "/"


@login_required
@require_GET
def profile(request):
    progressions = (
        Progression.objects.filter(user=request.user)
        .select_related("project", "study")
        .order_by("-updated_at")[:50]
    )
    return render(request, "library/profile.html", {"progressions": progressions})


def _widget_bootstrap(progression: Progression) -> dict:
    source = progression.source_json if isinstance(progression.source_json, dict) else {}
    prog = source.get("progression")
    if not prog or not prog.get("acordes"):
        prog = {
            "nombre": progression.title,
            "tonalidad": progression.key,
            "modo": progression.mode,
            "patron": (progression.ontology_json or {}).get("progression_meta", {}).get("patron"),
            "acordes": progression.analysis_json or [],
        }
    widget_state = source.get("widget_state") or progression.widget_state_json or {}
    selected = widget_state.get("selected_chord_index", source.get("selected_chord_index"))
    return {"progression": prog, "selected_chord_index": selected}


def _apply_progression_fields(progression: Progression, source: dict, derived: dict) -> None:
    progression.source_json = source
    progression.title = derived["title"]
    progression.key = derived["key"]
    progression.mode = derived["mode"]
    progression.chords_json = derived["chords_json"]
    progression.analysis_json = derived["analysis_json"]
    progression.ontology_json = derived["ontology_json"]
    progression.widget_state_json = derived["widget_state_json"]


@login_required
@require_GET
def progression_detail(request, uuid):
    progression = get_object_or_404(Progression, uuid=uuid, user=request.user)
    return render(
        request,
        "library/progression_detail.html",
        {
            "progression": progression,
            "widget_bootstrap": _widget_bootstrap(progression),
        },
    )


@require_POST
def progression_save(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "auth_required", "login_url": "/login/"},
            status=401,
        )
    try:
        source = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    if not isinstance(source, dict):
        return JsonResponse({"error": "Se esperaba un objeto JSON"}, status=400)

    derived = build_progression_payload(source)
    progression = Progression.objects.create(
        user=request.user,
        source_json=source,
        title=derived["title"],
        key=derived["key"],
        mode=derived["mode"],
        chords_json=derived["chords_json"],
        analysis_json=derived["analysis_json"],
        ontology_json=derived["ontology_json"],
        widget_state_json=derived["widget_state_json"],
    )
    return JsonResponse({
        "uuid": str(progression.uuid),
        "url": f"/progressions/{progression.uuid}/",
    }, status=201)


@require_POST
def progression_update(request, uuid):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "auth_required", "login_url": "/login/"},
            status=401,
        )
    progression = get_object_or_404(Progression, uuid=uuid, user=request.user)
    try:
        source = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    if not isinstance(source, dict):
        return JsonResponse({"error": "Se esperaba un objeto JSON"}, status=400)

    derived = build_progression_payload(source)
    _apply_progression_fields(progression, source, derived)
    progression.save()
    return JsonResponse({
        "uuid": str(progression.uuid),
        "url": f"/progressions/{progression.uuid}/",
    })


def _owns(user, progression: Progression) -> bool:
    return progression.user_id == user.id


@login_required
@require_GET
def progression_export(request, uuid):
    progression = get_object_or_404(Progression, uuid=uuid)
    if not _owns(request.user, progression):
        return HttpResponseForbidden()

    from django.utils import timezone

    data = {
        "uuid": str(progression.uuid),
        "title": progression.title,
        "key": progression.key,
        "mode": progression.mode,
        "source_json": progression.source_json,
        "chords_json": progression.chords_json,
        "analysis_json": progression.analysis_json,
        "ontology_json": progression.ontology_json,
        "widget_state_json": progression.widget_state_json,
        "project": {"id": progression.project_id, "title": progression.project.title} if progression.project else None,
        "study": {"id": progression.study_id, "title": progression.study.title} if progression.study else None,
        "exported_at": timezone.now().isoformat(),
    }
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 2})
