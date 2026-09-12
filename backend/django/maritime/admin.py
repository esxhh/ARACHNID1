from django.contrib import admin

from .models import SpillDetection, Vessel


@admin.register(Vessel)
class VesselAdmin(admin.ModelAdmin):
    list_display = ("name", "mmsi", "vessel_type", "flag", "status", "updated_at")
    list_filter = ("vessel_type", "flag", "status")
    search_fields = ("name", "mmsi")


@admin.register(SpillDetection)
class SpillDetectionAdmin(admin.ModelAdmin):
    list_display = ("name", "detection_id", "classification", "confidence", "detected_at")
    list_filter = ("classification",)
    search_fields = ("name", "detection_id")
