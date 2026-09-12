from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .train_real import SarTileDataset, evaluate
from .unet import load_oil_spill_model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a real SAR checkpoint on a held-out split.")
    parser.add_argument("--data", type=Path, default=Path("data/real_sar/test"))
    parser.add_argument("--checkpoint", type=Path, default=Path("models/oil_spill_unet_real.pt"))
    parser.add_argument("--device", default="cpu")
    arguments = parser.parse_args()
    dataset = SarTileDataset(arguments.data)
    score = evaluate(load_oil_spill_model(str(arguments.checkpoint), arguments.device), DataLoader(dataset, batch_size=4), arguments.device)
    print(f"test_tiles={len(dataset)} test_iou={score:.4f}")
