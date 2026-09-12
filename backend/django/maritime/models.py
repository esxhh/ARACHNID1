from django.db import models


class Vessel(models.Model):
    mmsi = models.CharField(max_length=9, unique=True)
    name = models.CharField(max_length=120)
    vessel_type = models.CharField(max_length=40)
    flag = models.CharField(max_length=3)
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed_knots = models.FloatField(default=0)
    course = models.FloatField(default=0)
    status = models.CharField(max_length=30, default="Underway")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.mmsi})"


class SpillDetection(models.Model):
    CLASSIFICATIONS = [
        ("OIL_SPILL", "Oil spill"),
        ("LOOK_ALIKE", "Look-alike"),
        ("UNVERIFIED", "Unverified"),
    ]

    detection_id = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    latitude = models.FloatField()
    longitude = models.FloatField()
    area_km2 = models.FloatField()
    confidence = models.FloatField()
    classification = models.CharField(max_length=20, choices=CLASSIFICATIONS)
    detected_at = models.DateTimeField()

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.detection_id}: {self.name}"
