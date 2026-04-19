#!/usr/bin/env python3
"""
Download/export large-v3-turbo model for offline bundling.
Run this once, then copy the output folder to models/large-v3-turbo.
"""

import os
from pathlib import Path
from faster_whisper import WhisperModel

def export_model(model_size="large-v3-turbo", device="cuda", output_dir="models"):
    print(f"Loading {model_size} on {device} to export...")

    # Load model (downloads if needed)
    model = WhisperModel(
        model_size,
        device=device,
        compute_type="float16",
        download_root=str(Path.home() / ".cache" / "whisper"),
    )

    # Create output directory
    output_path = Path(output_dir) / model_size
    output_path.mkdir(parents=True, exist_ok=True)

    # Copy model files from cache to output dir
    cache_dir = Path.home() / ".cache" / "whisper" / model_size
    if cache_dir.exists():
        print(f"Copying from cache: {cache_dir}")
        for item in cache_dir.iterdir():
            dest = output_path / item.name
            if item.is_file():
                dest.write_bytes(item.read_bytes())
                print(f"  Copied {item.name}")
            elif item.is_dir():
                dest.mkdir(exist_ok=True)
                print(f"  Created dir {item.name}")
    else:
        print("No cache found - model will be downloaded on first use.")

    print(f"Model exported to: {output_path}")
    print("Copy this folder to your project's models/large-v3-turbo/")
    print(f"Size: {sum(f.stat().st_size for f in output_path.rglob('*')) / 1024**2:.1f} MB")

if __name__ == "__main__":
    export_model()
