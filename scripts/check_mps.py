#!/usr/bin/env python3
"""
Quick check to confirm PyTorch can see GPU backends on macOS.
"""

import sys

import torch


def main() -> int:
    cuda_available = torch.cuda.is_available()
    mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()

    preferred_device = "mps" if mps_available else "cuda" if cuda_available else "cpu"

    print(f"torch version: {torch.__version__}")
    print(f"CUDA available: {cuda_available}")
    print(f"MPS available: {mps_available}")
    print(f"Using device: {preferred_device}")

    device = torch.device(preferred_device)
    tensor = torch.randn(1024, 1024, device=device)
    _ = torch.matmul(tensor, tensor)
    print(f"Successfully ran matmul on {preferred_device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
