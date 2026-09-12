from __future__ import annotations

try:
    import torch
    from torch import Tensor, nn
except ImportError as error:  # pragma: no cover - optional dependency
    raise RuntimeError("Install requirements-ml.txt to use the PyTorch oil-spill model") from error


class ConvBlock(nn.Module):
    def __init__(self, input_channels: int, output_channels: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(output_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(output_channels, output_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(output_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, features: Tensor) -> Tensor:
        return self.layers(features)


class OilSpillUNet(nn.Module):
    """Small SAR segmentation U-Net; weights must come from supervised training."""

    def __init__(self, input_channels: int = 2, output_channels: int = 1) -> None:
        super().__init__()
        self.down1 = ConvBlock(input_channels, 32)
        self.down2 = ConvBlock(32, 64)
        self.down3 = ConvBlock(64, 128)
        self.bridge = ConvBlock(128, 256)
        self.up3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.out = nn.Conv2d(32, output_channels, 1)
        self.pool = nn.MaxPool2d(2)

    def forward(self, image: Tensor) -> Tensor:
        first = self.down1(image)
        second = self.down2(self.pool(first))
        third = self.down3(self.pool(second))
        bridge = self.bridge(self.pool(third))
        decoded = self.up3(bridge)
        decoded = self.up2(decoded + third)
        decoded = self.up1(decoded + second)
        return self.out(decoded + first)


def load_oil_spill_model(checkpoint_path: str, device: str = "cpu") -> OilSpillUNet:
    model = OilSpillUNet().to(device)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint.get("model_state", checkpoint))
    model.eval()
    return model
