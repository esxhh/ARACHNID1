# Real SAR training data

Place verified Sentinel-1 SAR tiles here as `.npz` files. Each file must contain:

- `image`: a float32 array shaped `[2, H, W]` or `[H, W, 2]` for SAR channels
- `mask`: a binary array shaped `[H, W]`, where `1` means verified oil spill
- optional `ocean_mask`: a binary array shaped `[H, W]`; land pixels are forced to zero

Do not train on unverified dark spots. Keep the source scene ID, acquisition time, annotation source, and license in a dataset manifest outside the arrays.

Train from the project root:

```powershell
.\.venv\Scripts\python.exe -m ml.train_real --data data\real_sar --output models\oil_spill_unet_real.pt --epochs 20
```

The script prints validation IoU for each epoch and writes a checkpoint tagged `verified-real-sar`.
