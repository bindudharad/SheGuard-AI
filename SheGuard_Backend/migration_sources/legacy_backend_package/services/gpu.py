from __future__ import annotations

import logging
from dataclasses import dataclass


@dataclass
class GPUStatus:
    torch_available: bool
    cuda_available: bool
    device: str
    gpu_name: str | None = None
    memory_allocated_mb: float = 0.0
    memory_reserved_mb: float = 0.0
    error: str | None = None


def get_runtime_device(requested: str | None = None) -> str:
    if requested and requested.lower() not in {"auto", ""}:
        return requested
    status = get_gpu_status()
    return status.device


def get_gpu_status() -> GPUStatus:
    try:
        import torch
    except Exception as exc:
        return GPUStatus(False, False, "cpu", error=str(exc))

    cuda_available = bool(torch.cuda.is_available())
    if not cuda_available:
        return GPUStatus(True, False, "cpu")

    index = torch.cuda.current_device()
    return GPUStatus(
        torch_available=True,
        cuda_available=True,
        device=f"cuda:{index}",
        gpu_name=torch.cuda.get_device_name(index),
        memory_allocated_mb=torch.cuda.memory_allocated(index) / (1024 * 1024),
        memory_reserved_mb=torch.cuda.memory_reserved(index) / (1024 * 1024),
    )


def log_gpu_status(logger: logging.Logger | None = None) -> GPUStatus:
    logger = logger or logging.getLogger("sheguard")
    status = get_gpu_status()
    if status.cuda_available:
        logger.info(
            "CUDA enabled | device=%s | gpu=%s | allocated=%.1fMB | reserved=%.1fMB",
            status.device,
            status.gpu_name,
            status.memory_allocated_mb,
            status.memory_reserved_mb,
        )
    else:
        logger.info("CUDA unavailable; using CPU fallback | torch=%s | error=%s", status.torch_available, status.error)
    return status

