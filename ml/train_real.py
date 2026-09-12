from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader, Dataset, random_split

from .unet import OilSpillUNet


class SarTileDataset(Dataset):
    """Loads verified two-channel SAR tiles from .npz files.

    Each file must contain image [2,H,W] or [H,W,2], mask [H,W], and may contain
    ocean_mask [H,W]. Masks must be binary and land pixels must be zero.
    """

    def __init__(self, directory: Path) -> None:
        self.files = sorted(directory.glob("*.npz"))
        if not self.files:
            raise FileNotFoundError(f"No .npz SAR tiles found in {directory}")

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, index: int) -> tuple[Tensor, Tensor]:
        sample = np.load(self.files[index])
        image = sample["image"].astype("float32")
        mask = sample["mask"].astype("float32")
        if image.ndim != 3 or image.shape[0] not in (1, 2):
            if image.ndim == 3 and image.shape[-1] in (1, 2):
                image = np.moveaxis(image, -1, 0)
            else:
                raise ValueError(f"{self.files[index]} image must have one or two channels")
        if image.shape[0] == 1:
            image = np.concatenate([image, image], axis=0)
        if mask.shape != image.shape[1:]:
            raise ValueError(f"{self.files[index]} mask and image shapes do not match")
        if "ocean_mask" in sample:
            mask = mask * sample["ocean_mask"].astype("float32")
        return torch.from_numpy(image), torch.from_numpy(mask[None])


def dice_loss(logits: Tensor, target: Tensor) -> Tensor:
    probability = torch.sigmoid(logits)
    intersection = (probability * target).sum()
    return 1 - (2 * intersection + 1) / (probability.sum() + target.sum() + 1)


def evaluate(model: nn.Module, loader: DataLoader, device: str) -> float:
    model.eval()
    intersections = unions = 0
    with torch.inference_mode():
        for image, target in loader:
            prediction = torch.sigmoid(model(image.to(device))) >= 0.5
            target = target.to(device).bool()
            intersections += (prediction & target).sum().item()
            unions += (prediction | target).sum().item()
    return intersections / unions if unions else 1.0


def train(data_dir: Path, output: Path, epochs: int, device: str, validation_dir: Path | None = None) -> None:
    torch.manual_seed(42)
    random.seed(42)
    dataset = SarTileDataset(data_dir)
    if validation_dir:
        validation_set = SarTileDataset(validation_dir)
        train_set = dataset
    else:
        validation_size = max(1, len(dataset) // 5) if len(dataset) > 1 else 0
        train_size = len(dataset) - validation_size
        train_set, validation_set = random_split(dataset, [train_size, validation_size], generator=torch.Generator().manual_seed(42)) if validation_size else (dataset, [])
    train_loader = DataLoader(train_set, batch_size=4, shuffle=True)
    validation_loader = DataLoader(validation_set, batch_size=4) if len(validation_set) else None
    model = OilSpillUNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0003, weight_decay=0.0001)
    criterion = nn.BCEWithLogitsLoss()

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for image, target in train_loader:
            image, target = image.to(device), target.to(device)
            logits = model(image)
            loss = criterion(logits, target) + dice_loss(logits, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        validation_iou = evaluate(model, validation_loader, device) if validation_loader else 0.0
        print(f"epoch={epoch + 1}/{epochs} loss={running_loss / len(train_loader):.4f} validation_iou={validation_iou:.4f}")

    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "dataset": "verified-real-sar", "tiles": len(dataset), "epochs": epochs}, output)
    print(f"saved={output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ARACHNID on verified real SAR tiles.")
    parser.add_argument("--data", type=Path, default=Path("data/real_sar"))
    parser.add_argument("--output", type=Path, default=Path("models/oil_spill_unet_real.pt"))
    parser.add_argument("--validation-data", type=Path, default=None)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--device", default="cpu")
    arguments = parser.parse_args()
    train(arguments.data, arguments.output, arguments.epochs, arguments.device, arguments.validation_data)
