import json
from django.http import JsonResponse
from django.shortcuts import render
from jazz21.lydian import LydianSystem, distance_in_fifths, lydian_for_position

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
DISPLAY_NOTES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def explorer(request):
    tonic = request.GET.get("tonic", "F")
    if tonic not in [n for n in NOTES + DISPLAY_NOTES]:
        tonic = "F"
    return render(request, "lydian/explorer.html", {"tonic": tonic, "notes": DISPLAY_NOTES})


def api_system(request):
    tonic = request.GET.get("tonic", "F")
    try:
        ls = LydianSystem(tonic)
    except ValueError:
        return JsonResponse({"error": f"Unknown tonic: {tonic}"}, status=400)

    return JsonResponse({
        "tonic": tonic,
        "fifth_stack": ls.fifth_stack(),
        "regions": ls.regions(),
        "pedal_centers": ls.pedal_centers(),
        "modal_rank": ls.modal_rank(),
    })
