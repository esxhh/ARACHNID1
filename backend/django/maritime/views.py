from django.http import JsonResponse

from .models import SpillDetection, Vessel


def vessels_api(request):
    vessels = list(Vessel.objects.values(
        "mmsi", "name", "vessel_type", "flag", "latitude", "longitude",
        "speed_knots", "course", "status", "updated_at",
    ))
    return JsonResponse({"results": vessels})


def spills_api(request):
    spills = list(SpillDetection.objects.values(
        "detection_id", "name", "latitude", "longitude", "area_km2",
        "confidence", "classification", "detected_at",
    ))
    return JsonResponse({"results": spills})
