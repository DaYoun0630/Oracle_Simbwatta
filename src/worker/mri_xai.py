from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from matplotlib import cm
from PIL import Image

CAM_VISIBLE_PERCENTILE = 90.0
CAM_VISIBLE_ALPHA = 0.55
BRAIN_MASK_THRESHOLD = 0.05


ROI_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "hippocampus_L": {"center": (48, 54, 36), "sigma": 4.0},
    "hippocampus_R": {"center": (48, 54, 60), "sigma": 4.0},
    "entorhinal_L": {"center": (54, 48, 34), "sigma": 3.5},
    "entorhinal_R": {"center": (54, 48, 62), "sigma": 3.5},
    "parahippocampal_L": {"center": (48, 42, 32), "sigma": 4.0},
    "parahippocampal_R": {"center": (48, 42, 64), "sigma": 4.0},
    "amygdala_L": {"center": (42, 60, 34), "sigma": 3.5},
    "amygdala_R": {"center": (42, 60, 62), "sigma": 3.5},
    "posterior_cingulate": {"center": (30, 35, 48), "sigma": 5.0},
    "precuneus": {"center": (65, 30, 48), "sigma": 6.0},
    "middle_temporal_L": {"center": (48, 52, 24), "sigma": 8.0},
    "middle_temporal_R": {"center": (48, 52, 72), "sigma": 8.0},
    "inferior_temporal_L": {"center": (42, 60, 22), "sigma": 8.0},
    "inferior_temporal_R": {"center": (42, 60, 72), "sigma": 8.0},
    "fusiform_L": {"center": (38, 58, 28), "sigma": 6.0},
    "fusiform_R": {"center": (38, 58, 68), "sigma": 6.0},
    "parietal_L": {"center": (68, 45, 26), "sigma": 8.0},
    "parietal_R": {"center": (68, 45, 70), "sigma": 8.0},
    "frontal": {"center": (55, 85, 48), "sigma": 10.0},
    "lateral_ventricle": {"center": (35, 56, 48), "sigma": 12.0},
    "inferior_horn_L": {"center": (35, 56, 30), "sigma": 8.0},
    "inferior_horn_R": {"center": (35, 56, 66), "sigma": 8.0},
}


REGION_GROUPS: Dict[str, Tuple[str, ...]] = {
    "Hippocampus": (
        "hippocampus_L",
        "hippocampus_R",
        "parahippocampal_L",
        "parahippocampal_R",
        "amygdala_L",
        "amygdala_R",
    ),
    "Entorhinal": ("entorhinal_L", "entorhinal_R"),
    "Temporal": (
        "middle_temporal_L",
        "middle_temporal_R",
        "inferior_temporal_L",
        "inferior_temporal_R",
        "fusiform_L",
        "fusiform_R",
    ),
    "Parietal": (
        "precuneus",
        "posterior_cingulate",
        "parietal_L",
        "parietal_R",
        "frontal",
    ),
    "Ventricle": ("lateral_ventricle", "inferior_horn_L", "inferior_horn_R"),
}

PLANE_ORDER: Tuple[str, ...] = ("axial", "coronal", "sagittal")
PLANE_TO_DIM: Dict[str, int] = {
    "axial": 2,
    "coronal": 1,
    "sagittal": 0,
}


def _normalize01(array: np.ndarray) -> np.ndarray:
    array = np.nan_to_num(array.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    min_val = float(array.min())
    max_val = float(array.max())
    if max_val <= min_val:
        return np.zeros_like(array, dtype=np.float32)
    return (array - min_val) / (max_val - min_val)


def _create_brain_mask(volume_norm: np.ndarray, threshold: float = BRAIN_MASK_THRESHOLD) -> np.ndarray:
    return (volume_norm > threshold).astype(np.float32)


def _percentile_in_mask(
    cam_norm: np.ndarray,
    brain_mask: np.ndarray,
    percentile: float = CAM_VISIBLE_PERCENTILE,
    fallback: float = 0.5,
) -> float:
    if brain_mask.shape != cam_norm.shape:
        return float(fallback)
    values = cam_norm[brain_mask > 0]
    values = values[values > 0]
    if values.size == 0:
        return float(fallback)
    return float(np.percentile(values, percentile))


def _pick_slice_index(cam_energy: np.ndarray, brain_area: np.ndarray) -> int:
    """Pick slice near CAM center while avoiding edge slices with tiny brain area."""
    cam_energy = np.asarray(cam_energy, dtype=np.float32)
    brain_area = np.asarray(brain_area, dtype=np.float32)
    if cam_energy.size == 0:
        return 0

    if brain_area.size != cam_energy.size:
        if float(cam_energy.max()) > 0.0:
            return int(np.argmax(cam_energy))
        return int(cam_energy.size // 2)

    max_area = float(np.max(brain_area)) if brain_area.size else 0.0
    if max_area <= 0.0:
        if float(cam_energy.max()) > 0.0:
            return int(np.argmax(cam_energy))
        return int(cam_energy.size // 2)

    # Keep only slices with enough anatomy to avoid torn / edge-looking views.
    valid_idx = np.where(brain_area >= max_area * 0.60)[0]
    if valid_idx.size == 0:
        valid_idx = np.arange(cam_energy.size, dtype=np.int64)

    # If CAM is weak on this axis, show the most anatomical slice.
    valid_energy = np.clip(cam_energy[valid_idx], 0.0, None)
    if float(valid_energy.max()) <= 0.0:
        return int(valid_idx[np.argmax(brain_area[valid_idx])])

    # Weighted center of CAM within anatomical slices, then snap to nearest valid index.
    weighted_center = float(np.dot(valid_idx.astype(np.float32), valid_energy) / (valid_energy.sum() + 1e-6))
    nearest_pos = int(np.argmin(np.abs(valid_idx.astype(np.float32) - weighted_center)))
    return int(valid_idx[nearest_pos])


def _largest_component_2d(mask: np.ndarray) -> np.ndarray:
    """Keep only the largest connected component in a 2D binary mask."""
    if mask.ndim != 2:
        return mask.astype(bool)
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    best_count = 0
    best_points: list[tuple[int, int]] = []

    for r in range(h):
        for c in range(w):
            if not mask[r, c] or visited[r, c]:
                continue

            stack = [(r, c)]
            visited[r, c] = True
            points: list[tuple[int, int]] = []

            while stack:
                rr, cc = stack.pop()
                points.append((rr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = rr + dr, cc + dc
                    if nr < 0 or nr >= h or nc < 0 or nc >= w:
                        continue
                    if visited[nr, nc] or not mask[nr, nc]:
                        continue
                    visited[nr, nc] = True
                    stack.append((nr, nc))

            if len(points) > best_count:
                best_count = len(points)
                best_points = points

    out = np.zeros((h, w), dtype=bool)
    for rr, cc in best_points:
        out[rr, cc] = True
    return out


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
        cam_raw = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = torch.relu(cam_raw)
        # Some cases (especially CN target) can become all-zero after ReLU.
        # Fallback to absolute saliency to avoid blank CAM outputs.
        if float(cam.max().detach().cpu()) <= 1e-8:
            cam = torch.abs(cam_raw)
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


def _extract_plane_slice(volume: np.ndarray, plane: str, index: int) -> np.ndarray:
    dim = PLANE_TO_DIM.get(plane)
    if dim is None:
        raise ValueError(f"Unsupported plane: {plane}")

    max_index = volume.shape[dim] - 1
    safe_index = max(0, min(int(index), max_index))

    # NOTE:
    # For this pipeline's resampled tensor layout (D, H, W):
    # - axial   -> dim 2
    # - coronal -> dim 1
    # - sagittal-> dim 0
    if dim == 0:
        return volume[safe_index, :, :]
    if dim == 1:
        return volume[:, safe_index, :]
    return volume[:, :, safe_index]


def _save_attention_overlay_for_plane(
    base_norm: np.ndarray,
    cam_norm: np.ndarray,
    brain_mask: np.ndarray,
    cam_threshold: float,
    plane: str,
    slice_index: int,
    output_path: Path,
) -> None:
    base_slice = _extract_plane_slice(base_norm, plane, slice_index)
    cam_slice = _extract_plane_slice(cam_norm, plane, slice_index)
    brain_slice_raw = _extract_plane_slice(brain_mask, plane, slice_index)
    brain_slice_bool = _largest_component_2d(brain_slice_raw > 0)
    brain_slice = brain_slice_bool.astype(np.float32)

    # Render attention with slice-local normalization so CAM remains visible
    # even when absolute activations are small.
    base_display = base_slice * brain_slice + (1.0 - brain_slice) * 0.45
    local_vals = cam_slice[brain_slice > 0]
    local_vals = local_vals[local_vals > 0]

    heat_scaled = np.zeros_like(cam_slice, dtype=np.float32)
    if local_vals.size > 0:
        high = float(np.max(local_vals))
        if high > 0.0:
            heat_scaled = np.clip(cam_slice / (high + 1e-6), 0.0, 1.0).astype(np.float32)

    heat_scaled = np.power(heat_scaled, 0.7, dtype=np.float32)
    heat_scaled *= (brain_slice > 0).astype(np.float32)

    alpha = CAM_VISIBLE_ALPHA * np.power(heat_scaled, 0.35, dtype=np.float32)
    alpha = np.where(heat_scaled > 0.02, np.maximum(alpha, 0.12), 0.0).astype(np.float32)

    base_rgb = np.stack([base_display, base_display, base_display], axis=-1)
    heat_rgb = cm.get_cmap("turbo")(heat_scaled)[..., :3]
    blended = (1.0 - alpha[..., None]) * base_rgb + alpha[..., None] * heat_rgb
    blended = np.clip(blended, 0.0, 1.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((blended * 255.0).astype(np.uint8)).save(output_path)


def _save_attention_overlays(
    base_volume: np.ndarray,
    cam_volume: np.ndarray,
    output_path: str,
) -> Tuple[Dict[str, str], Dict[str, int]]:
    base_norm = _normalize01(base_volume)
    cam_norm = _normalize01(cam_volume)
    brain_mask = _create_brain_mask(base_norm, threshold=BRAIN_MASK_THRESHOLD)
    cam_threshold = _percentile_in_mask(
        cam_norm,
        brain_mask,
        percentile=CAM_VISIBLE_PERCENTILE,
        fallback=0.5,
    )

    # Pick per-plane slices where CAM energy is maximal inside brain mask.
    masked_cam = cam_norm * brain_mask
    axial_energy = masked_cam.sum(axis=(0, 1))      # dim2
    coronal_energy = masked_cam.sum(axis=(0, 2))    # dim1
    sagittal_energy = masked_cam.sum(axis=(1, 2))   # dim0

    axial_area = brain_mask.sum(axis=(0, 1))       # dim2
    coronal_area = brain_mask.sum(axis=(0, 2))     # dim1
    sagittal_area = brain_mask.sum(axis=(1, 2))    # dim0

    if float(axial_energy.max()) <= 0.0 and float(coronal_energy.max()) <= 0.0 and float(sagittal_energy.max()) <= 0.0:
        peak_d, peak_h, peak_w = np.unravel_index(int(np.argmax(cam_norm)), cam_norm.shape)
        slice_indices = {
            "axial": int(peak_w),
            "coronal": int(peak_h),
            "sagittal": int(peak_d),
        }
    else:
        slice_indices = {
            "axial": _pick_slice_index(axial_energy, axial_area),
            "coronal": _pick_slice_index(coronal_energy, coronal_area),
            "sagittal": _pick_slice_index(sagittal_energy, sagittal_area),
        }

    output_file = Path(output_path)
    suffix = output_file.suffix if output_file.suffix else ".png"
    stem = output_file.stem if output_file.stem else "cam"
    parent = output_file.parent

    local_paths = {
        "axial": str(output_file),
        "coronal": str(parent / f"{stem}_coronal{suffix}"),
        "sagittal": str(parent / f"{stem}_sagittal{suffix}"),
    }

    for plane in PLANE_ORDER:
        plane_path = Path(local_paths[plane])
        _save_attention_overlay_for_plane(
            base_norm=base_norm,
            cam_norm=cam_norm,
            brain_mask=brain_mask,
            cam_threshold=cam_threshold,
            plane=plane,
            slice_index=slice_indices[plane],
            output_path=plane_path,
        )

    return local_paths, slice_indices


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

    # Gentle smoothing only. Heavy smoothing distorts localization and can
    # pull attention to edge slices.
    cam_volume = _normalize01(cam_volume)
    cam_smooth = torch.tensor(cam_volume).unsqueeze(0).unsqueeze(0)
    cam_smooth = torch.nn.functional.avg_pool3d(cam_smooth, kernel_size=3, stride=1, padding=1)
    cam_volume = _normalize01(cam_smooth.squeeze().cpu().numpy().astype(np.float32))

    local_paths, slice_indices = _save_attention_overlays(base_volume, cam_volume, output_path)
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

    attention_maps = [
        {
            "plane": plane,
            "local_path": local_paths[plane],
            "sliceIndex": int(slice_indices[plane]),
        }
        for plane in PLANE_ORDER
    ]

    return {
        "local_path": local_paths["axial"],
        "local_paths": local_paths,
        "attentionMaps": attention_maps,
        "method": "GradCAM3D",
        "stage": stage_name,
        "targetLabel": target_label,
        "targetClassIndex": int(target_class_idx),
        "sliceIndex": int(slice_indices["axial"]),
        "sliceIndices": {k: int(v) for k, v in slice_indices.items()},
        "regionContributions": region_contributions,
        "roiScores": roi_scores_ranked[:10],
    }
