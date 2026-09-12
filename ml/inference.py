from __future__ import annotations

try:
    import torch
    from torch import Tensor
except ImportError as error:  # pragma: no cover - optional dependency
    raise RuntimeError("Install requirements-ml.txt to use PyTorch inference") from error

from .unet import OilSpillUNet


def segment_ocean_candidate(model: OilSpillUNet, image: Tensor, ocean_mask: Tensor, threshold: float = 0.65) -> dict:
    """Run segmentation and force all land pixels out of the returned mask."""
    if image.ndim != 4 or image.shape[1] != 2:
        raise ValueError("Expected image tensor with shape [batch, 2, height, width]")
    if ocean_mask.shape != image[:, :1].shape:
        raise ValueError("Ocean mask must match image spatial shape")
    with torch.inference_mode():
        probabilities = torch.sigmoid(model(image))
    clean_mask = (probabilities >= threshold) & ocean_mask.bool()
    confidence = float(probabilities[clean_mask].mean().item()) if clean_mask.any() else 0.0
    return {
        "mask": clean_mask.cpu().numpy().tolist(),
        "confidence": round(confidence, 4),
        "classification": "OIL_SPILL" if confidence >= threshold else "LOOK_ALIKE",
        "land_pixels_removed": int((~ocean_mask.bool()).sum().item()),
    }
