from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from matplotlib import cm
from PIL import Image


ROI_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "hippocampus_L": {"center": (48, 54, 36), "sigma": 4.0},
    "hippocampus_R": {"center": (48, 54, 60), "sigma": 4.0},
    "entorhinal_L": {"center": (54, 48, 34), "sigma": 3.5},
    "entorhinal_R": {"center": (54, 48, 62), "sigma": 3.5},
    "middle_temporal_L": {"center": (48, 52, 24), "sigma": 8.0},
    "middle_temporal_R": {"center": (48, 52, 72), "sigma": 8.0},
    "inferior_temporal_L": {"center": (42, 60, 22), "sigma": 8.0},
    "inferior_temporal_R": {"center": (42, 60, 72), "sigma": 8.0},
    "precuneus": {"center": (65, 30, 48), "sigma": 6.0},
    "posterior_cingulate": {"center": (30, 35, 48), "sigma": 5.0},
    "parietal_L": {"center": (68, 45, 26), "sigma": 8.0},
    "parietal_R": {"center": (68, 45, 70), "sigma": 8.0},
    "lateral_ventricle": {"center": (35, 56, 48), "sigma": 12.0},
}


REGION_GROUPS: Dict[str, Tuple[str, ...]] = {
    "Hippocampus": ("hippocampus_L", "hippocampus_R"),
    "Entorhinal": ("entorhinal_L", "entorhinal_R"),
    "Temporal": (
        "middle_temporal_L",
        "middle_temporal_R",
        "inferior_temporal_L",
        "inferior_temporal_R",
    ),
    "Parietal": ("precuneus", "posterior_cingulate", "parietal_L", "parietal_R"),
    "Ventricle": ("lateral_ventricle",),
}


def _normalize01(array: np.ndarray) -> np.ndarray:
    array = np.nan_to_num(array.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    min_val = float(array.min())
    max_val = float(array.max())
    if max_val <= min_val:
        return np.zeros_like(array, dtype=np.float32)
    return (array - min_val) / (max_val - min_val)


def _severity_from_percentage(percentage: float) -> str:
    if percentage >= 35.0:
        return "high"
    if percentage >= 20.0:
        return "medium"
    return "low"


def _resolve_target_layer(model: nn.Module):
    if hasattr(model, "encoder"):
        return model.encoder[-1].block[3]
    if hasattr(model, "block4") and hasattr(model.block4, "block"):
        return model.block4.block[3]

    last_conv = None
    for module in model.modules():
        if isinstance(module, nn.Conv3d):
            last_conv = module
    if last_conv is None:
        raise RuntimeError("Grad-CAM target layer not found")
    return last_conv


class GradCAM3D:
    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.activations = None
        self.gradients = None
        self._handles = [
            target_layer.register_forward_hook(self._forward_hook),
            target_layer.register_full_backward_hook(self._backward_hook),
        ]

    def _forward_hook(self, _module, _inputs, output):
        self.activations = output

    def _backward_hook(self, _module, _grad_input, grad_output):
        self.gradients = grad_output[0]

    def remove(self):
        for handle in self._handles:
            handle.remove()
        self._handles = []

    def __call__(self, x: torch.Tensor, class_idx: int) -> torch.Tensor:
        self.model.zero_grad(set_to_none=True)
        logits = self.model(x)
        logits[:, int(class_idx)].sum().backward()
        weights = self.gradients.mean(dim=(2, 3, 4), keepdim=True)
        cam = torch.relu((weights * self.activations).sum(dim=1, keepdim=True))
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-6)
        return cam


def _gaussian_mask(shape: Tuple[int, int, int], center: Tuple[int, int, int], sigma: float) -> np.ndarray:
    depth, height, width = shape
    zz, yy, xx = np.meshgrid(
        np.arange(depth, dtype=np.float32),
        np.arange(height, dtype=np.float32),
        np.arange(width, dtype=np.float32),
        indexing="ij",
    )
    cz, cy, cx = center
    dist_sq = ((zz - cz) ** 2) + ((yy - cy) ** 2) + ((xx - cx) ** 2)
    return np.exp(-dist_sq / (2.0 * (sigma ** 2) + 1e-6)).astype(np.float32)


def _compute_roi_scores(cam_volume: np.ndarray) -> Dict[str, float]:
    roi_scores: Dict[str, float] = {}
    for roi_name, roi_info in ROI_DEFINITIONS.items():
        center = tuple(int(v) for v in roi_info["center"])
        sigma = float(roi_info["sigma"])
        mask = _gaussian_mask(cam_volume.shape, center=center, sigma=sigma)
        score = float((cam_volume * mask).sum() / (mask.sum() + 1e-6))
        roi_scores[roi_name] = score
    return roi_scores


def _aggregate_region_contributions(roi_scores: Dict[str, float]) -> List[Dict[str, object]]:
    region_raw: Dict[str, float] = {}
    for region_name, roi_keys in REGION_GROUPS.items():
        values = [roi_scores.get(roi_key, 0.0) for roi_key in roi_keys]
        region_raw[region_name] = float(np.mean(values)) if values else 0.0

    total = float(sum(max(value, 0.0) for value in region_raw.values()))
    if total <= 1e-9:
        return []

    contributions = []
    for region_name, value in region_raw.items():
        percentage = (max(value, 0.0) / total) * 100.0
        contributions.append(
            {
                "region": region_name,
                "percentage": round(float(percentage), 1),
                "severity": _severity_from_percentage(float(percentage)),
            }
        )

    contributions.sort(key=lambda item: float(item["percentage"]), reverse=True)
    return contributions


def _save_attention_overlay(
    base_volume: np.ndarray,
    cam_volume: np.ndarray,
    output_path: str,
) -> int:
    base_norm = _normalize01(base_volume)
    cam_norm = _normalize01(cam_volume)

    axial_scores = cam_norm.mean(axis=(1, 2))
    slice_index = int(np.argmax(axial_scores))

    base_slice = np.rot90(base_norm[slice_index], 2)
    cam_slice = np.rot90(cam_norm[slice_index], 2)

    threshold = float(np.quantile(cam_slice, 0.75))
    alpha = np.clip((cam_slice - threshold) / (1.0 - threshold + 1e-6), 0.0, 1.0) * 0.8

    base_rgb = np.stack([base_slice, base_slice, base_slice], axis=-1)
    heat_rgb = cm.get_cmap("turbo")(cam_slice)[..., :3]
    blended = (1.0 - alpha[..., None]) * base_rgb + alpha[..., None] * heat_rgb
    blended = np.clip(blended, 0.0, 1.0)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((blended * 255.0).astype(np.uint8)).save(output_file)
    return slice_index


def generate_attention_artifacts(
    model: nn.Module,
    input_tensor: torch.Tensor,
    base_volume: np.ndarray,
    target_class_idx: int,
    output_path: str,
    stage_name: str,
    target_label: str,
) -> Dict[str, object]:
    target_layer = _resolve_target_layer(model)
    cam_runner = GradCAM3D(model, target_layer)
    try:
        with torch.enable_grad():
            cam_tensor = cam_runner(input_tensor, class_idx=target_class_idx)
    finally:
        cam_runner.remove()

    cam_volume = cam_tensor.detach().cpu().numpy()[0, 0].astype(np.float32)
    if cam_volume.shape != base_volume.shape:
        resized = torch.tensor(cam_volume).unsqueeze(0).unsqueeze(0)
        resized = torch.nn.functional.interpolate(
            resized,
            size=base_volume.shape,
            mode="trilinear",
            align_corners=False,
        )
        cam_volume = resized.squeeze().cpu().numpy().astype(np.float32)

    slice_index = _save_attention_overlay(base_volume, cam_volume, output_path)
    roi_scores = _compute_roi_scores(cam_volume)
    region_contributions = _aggregate_region_contributions(roi_scores)

    roi_scores_ranked = sorted(
        (
            {"roi": roi_name, "score": round(float(score), 6)}
            for roi_name, score in roi_scores.items()
        ),
        key=lambda item: item["score"],
        reverse=True,
    )

    return {
        "local_path": str(output_path),
        "method": "GradCAM3D",
        "stage": stage_name,
        "targetLabel": target_label,
        "targetClassIndex": int(target_class_idx),
        "sliceIndex": int(slice_index),
        "regionContributions": region_contributions,
        "roiScores": roi_scores_ranked[:10],
    }

