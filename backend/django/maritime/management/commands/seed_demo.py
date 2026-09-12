from datetime import datetime

from django.core.management.base import BaseCommand
from maritime.models import SpillDetection, Vessel


VESSELS = [
    ("636019874", "Northwind Trader", "Tanker", "LR", 25.18, 55.31, 12.4, 92, "Underway"),
    ("477091200", "Blue Meridian", "Cargo", "HK", 25.43, 55.05, 8.7, 261, "Underway"),
    ("538008912", "Asteria", "Tanker", "MH", 25.31, 55.62, 10.1, 78, "Underway"),
    ("311000742", "Pelagic Dawn", "Cargo", "BS", 25.03, 55.68, 6.3, 184, "Anchored"),
    ("367772910", "Coastal Sentinel", "Service", "US", 25.55, 55.46, 14.8, 135, "Underway"),
    ("249781000", "Silver Current", "Tanker", "MT", 24.82, 55.18, 11.2, 24, "Underway"),
]

SPILLS = [
    ("SPL-2026-0912-01", "Jebel Ali dark spot", 25.24, 55.48, 4.8, 0.91, "OIL_SPILL", "2026-09-12T05:40:00+00:00"),
    ("SPL-2026-0911-03", "Offshore look-alike", 24.98, 55.83, 2.1, 0.63, "LOOK_ALIKE", "2026-09-11T18:15:00+00:00"),
]


class Command(BaseCommand):
    help = "Load the Ocean Eye demo vessels and spill detections."

    def handle(self, *args, **options):
        for row in VESSELS:
            Vessel.objects.update_or_create(
                mmsi=row[0],
                defaults={
                    "name": row[1],
                    "vessel_type": row[2],
                    "flag": row[3],
                    "latitude": row[4],
                    "longitude": row[5],
                    "speed_knots": row[6],
                    "course": row[7],
                    "status": row[8],
                },
            )

        for row in SPILLS:
            SpillDetection.objects.update_or_create(
                detection_id=row[0],
                defaults={
                    "name": row[1],
                    "latitude": row[2],
                    "longitude": row[3],
                    "area_km2": row[4],
                    "confidence": row[5],
                    "classification": row[6],
                    "detected_at": datetime.fromisoformat(row[7].replace("Z", "+00:00")),
                },
            )

        self.stdout.write(self.style.SUCCESS("Loaded 6 vessels and 2 spill detections."))
