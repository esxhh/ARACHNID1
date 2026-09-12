from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch import Tensor, nn

from .unet import OilSpillUNet


def make_batch(batch_size: int, size: int, device: str) -> tuple[Tensor, Tensor, Tensor]:
    image = torch.randn(batch_size, 2, size, size, device=device) * 0.08
    target = torch.zeros(batch_size, 1, size, size, device=device)
    ocean_mask = torch.ones(batch_size, 1, size, size, dtype=torch.bool, device=device)
    land_height = torch.randint(size // 8, size // 3, (batch_size,), device=device)

    for index in range(batch_size):
        ocean_mask[index, :, : land_height[index], :] = False
        center_y = torch.randint(land_height[index] + 8, size - 8, (1,)).item()
        center_x = torch.randint(8, size - 8, (1,)).item()
        radius_y = torch.randint(3, 10, (1,)).item()
        radius_x = torch.randint(6, 16, (1,)).item()
        y_grid, x_grid = torch.meshgrid(torch.arange(size, device=device), torch.arange(size, device=device), indexing="ij")
        blob = (((y_grid - center_y) / radius_y) ** 2 + ((x_grid - center_x) / radius_x) ** 2) <= 1
        blob &= ocean_mask[index, 0]
        target[index, 0] = blob.float()
        image[index, 0, blob] -= 0.45
        image[index, 1, blob] += 0.25

    return image, target, ocean_mask


def train(output: Path, steps: int, device: str) -> None:
    torch.manual_seed(42)
    model = OilSpillUNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_function = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([6.0], device=device))
    model.train()

    for step in range(steps):
        image, target, ocean_mask = make_batch(8, 64, device)
        logits = model(image)
        loss = loss_function(logits[ocean_mask], target[ocean_mask])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if (step + 1) % max(1, steps // 5) == 0:
            print(f"step={step + 1}/{steps} loss={loss.item():.4f}")

    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "dataset": "synthetic-sar-demo", "steps": steps}, output)
    print(f"saved={output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a development-only synthetic SAR checkpoint.")
    parser.add_argument("--output", type=Path, default=Path("models/oil_spill_unet_demo.pt"))
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--device", default="cpu")
    arguments = parser.parse_args()
    train(arguments.output, arguments.steps, arguments.device)
