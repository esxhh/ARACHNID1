from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image


def normalize(array: np.ndarray) -> np.ndarray:
    low, high = np.percentile(array, [1, 99])
    if high <= low:
        return np.zeros_like(array, dtype="float32")
    return np.clip((array - low) / (high - low), 0, 1).astype("float32")


def prepare(source: Path, output: Path, size: tuple[int, int]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        split_output = output / split
        split_output.mkdir(parents=True, exist_ok=True)
        manifest = source / "splits" / f"{split}.csv"
        with manifest.open(newline="", encoding="utf-8") as handle:
            rows = csv.DictReader(handle)
            for row in rows:
                sample_id = row["sample_id"]
                raster_16 = source / "RASTER" / "IMG-TIFF" / "16-BIT" / f"{sample_id}.tiff"
                raster_8 = source / "RASTER" / "IMG-TIFF" / "8-BIT" / f"{sample_id}.tiff"
                mask_path = source / row["mask_path"]
                image_16 = np.asarray(Image.open(raster_16).resize(size, Image.Resampling.BILINEAR), dtype="float32")
                image_8 = np.asarray(Image.open(raster_8).resize(size, Image.Resampling.BILINEAR), dtype="float32")
                mask = np.asarray(Image.open(mask_path).resize(size, Image.Resampling.NEAREST), dtype="uint8")
                image = np.stack([normalize(image_16), normalize(image_8)])
                np.savez_compressed(split_output / f"{sample_id}.npz", image=image, mask=(mask > 0).astype("uint8"), split=split)
    print(f"prepared={len(list(output.glob('**/*.npz')))} tiles output={output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert the Garcia-INPE Sentinel-1 dataset to ARACHNID NPZ tiles.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/real_sar"))
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=192)
    arguments = parser.parse_args()
    prepare(arguments.source, arguments.output, (arguments.width, arguments.height))
