from dataclasses import dataclass


@dataclass(frozen=True)
class ScreeningResult:
    classification: str
    confidence: float
    reason: str


def screen_candidate(
    *,
    is_land: bool,
    distance_to_shore_km: float,
    darkness_score: float,
    texture_score: float,
    wind_speed_ms: float,
) -> ScreeningResult:
    """Conservative pre-inference screen for SAR dark-spot candidates.

    This is a deterministic guardrail, not a trained segmentation model. It rejects
    land and shoreline artifacts before a future PyTorch model is called.
    """
    if is_land:
        return ScreeningResult("LOOK_ALIKE", 0.01, "Candidate is inside the land mask")
    if distance_to_shore_km < 1:
        return ScreeningResult("LOOK_ALIKE", 0.08, "Candidate is too close to shore")

    darkness = max(0, min(1, darkness_score))
    texture = max(0, min(1, texture_score))
    low_wind = max(0, min(1, 1 - wind_speed_ms / 15))
    confidence = 0.45 * darkness + 0.35 * texture + 0.20 * low_wind
    classification = "OIL_SPILL" if confidence >= 0.68 else "LOOK_ALIKE"
    reason = "Ocean candidate passes conservative SAR screening" if classification == "OIL_SPILL" else "Insufficient SAR evidence; manual review required"
    return ScreeningResult(classification, round(confidence, 3), reason)
