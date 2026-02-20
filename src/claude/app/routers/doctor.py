from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse, Response
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel
import logging
from datetime import date, datetime
from pathlib import Path
from collections import deque
import os
import gzip
import struct
import zlib
import json
import re

from .. import db
from ..schemas.patient import PatientOut, PatientCreate, PatientUpdate, PatientWithUser
from ..schemas.recording import RecordingOut
from ..schemas.assessment import VoiceAssessmentOut, MRIAssessmentOut
from ..schemas.diagnosis import DiagnosisOut, DiagnosisCreate, DiagnosisUpdate
from ..schemas.family import FamilyMemberOut, FamilyMemberCreate
from ..storage import storage

router = APIRouter(prefix="/api/doctor", tags=["doctor"])
logger = logging.getLogger(__name__)
MRI_RENDER_VERSION = "20260213-8"
SUBJECT_ID_PATTERN = re.compile(r"(\d{3}_S_\d{4})", re.IGNORECASE)
MRI_DIAGNOSIS_COLUMN_MAP: Dict[str, str] = {
    "hippocampus_atrophy": "hippocampal_atrophy",
    "temporal_lobe_atrophy": "medial_temporal_atrophy",
    "total_brain_volume_loss": "global_brain_volume_decrease",
    "white_matter_lesion": "white_matter_lesions",
    "frontal_lobe_atrophy": "frontal_atrophy",
    "parietal_lobe_atrophy": "parietal_atrophy",
}


class MRIDoctorDiagnosisPayload(BaseModel):
    diagnoses: List[str]
    additionalNotes: Optional[str] = None
    timestamp: Optional[datetime] = None
    doctorId: Optional[str] = None


# TODO: Add auth dependency to verify user is a doctor
# from ..auth.dependencies import get_current_doctor


def _iter_processed_dirs():
    env_dir = os.getenv("MCI_PROCESSED_DIR")
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if candidate.is_dir():
            yield candidate

    # Docker api container mount path.
    docker_path = Path("/app/minio-data/processed")
    if docker_path.is_dir():
        yield docker_path

    # Local development fallback path.
    local_path = Path("/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/minio-data/processed")
    if local_path.is_dir():
        yield local_path

    relative_path = Path("minio-data/processed")
    if relative_path.is_dir():
        yield relative_path


def _iter_raw_mri_dirs():
    env_dir = os.getenv("MCI_RAW_MRI_DIR")
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if candidate.is_dir():
            yield candidate

    # Docker api container mount path.
    docker_path = Path("/app/data/raw/mri")
    if docker_path.is_dir():
        yield docker_path

    # Local development fallback path.
    local_path = Path("/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/data/raw/mri")
    if local_path.is_dir():
        yield local_path

    relative_path = Path("data/raw/mri")
    if relative_path.is_dir():
        yield relative_path


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _preprocessed_rank(path: Path):
    """Prefer non-2mm preprocessed files first, then newer files."""
    name = path.name.lower()
    is_2mm = ("_2mm_" in name) or name.endswith("_2mm_preprocessed.nii.gz")
    return (1 if is_2mm else 0, -_safe_mtime(path))


def _find_preprocessed_nifti(subject_id: str) -> Optional[Path]:
    normalized_id = (subject_id or "").strip()
    if not normalized_id:
        return None

    for processed_dir in _iter_processed_dirs():
        exact = processed_dir / f"{normalized_id}.nii.gz"
        if exact.is_file():
            return exact

        matches = sorted(processed_dir.glob(f"*{normalized_id}*.nii.gz"), key=_preprocessed_rank)
        if matches:
            return matches[0]

        # Some pipelines archive processed outputs under subdirectories
        # (e.g. processed/archive). Search recursively as fallback.
        recursive_matches = sorted(
            (path for path in processed_dir.rglob("*.nii.gz") if normalized_id in path.name),
            key=_preprocessed_rank,
        )
        if recursive_matches:
            return recursive_matches[0]

    return None


def _find_original_dicom_series_dir(subject_id: str) -> Optional[Path]:
    normalized_id = (subject_id or "").strip()
    if not normalized_id:
        return None

    for raw_root in _iter_raw_mri_dirs():
        subject_dir = raw_root / normalized_id
        if not subject_dir.is_dir():
            matches = sorted(
                (path for path in raw_root.glob(f"*{normalized_id}*") if path.is_dir()),
                key=_safe_mtime,
                reverse=True,
            )
            subject_dir = matches[0] if matches else None

        if not subject_dir:
            continue

        counts = {}
        for dcm_path in subject_dir.rglob("*.dcm"):
            parent = dcm_path.parent
            counts[parent] = counts.get(parent, 0) + 1

        if not counts:
            continue

        best_dir, _ = max(
            counts.items(),
            key=lambda item: (item[1], _safe_mtime(item[0])),
        )
        return best_dir

    return None


def _extract_subject_id_from_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    matched = SUBJECT_ID_PATTERN.search(text)
    if not matched:
        return None

    return matched.group(0).upper()


def _resolve_bucket_and_key(path: str, default_bucket: str = "mri-xai"):
    raw = str(path or "").strip().replace("s3://", "")
    if not raw:
        raise ValueError("Object path is empty")
    if "/" not in raw:
        return default_bucket, raw

    bucket, key = raw.split("/", 1)
    known_buckets = {
        "voice-recordings",
        "voice-transcript",
        "processed",
        "mri-scans",
        "exports",
        "mri-preprocessed",
        "mri-xai",
        default_bucket,
    }
    if bucket in known_buckets:
        return bucket, key
    return default_bucket, raw


def _resolve_attention_map_object(ai_analysis: Dict[str, Any]) -> Optional[tuple[str, str]]:
    if not isinstance(ai_analysis, dict):
        return None

    object_path = ai_analysis.get("attentionMapObject")
    if isinstance(object_path, str) and object_path.strip():
        try:
            return _resolve_bucket_and_key(object_path.strip(), default_bucket="mri-xai")
        except Exception:
            return None

    object_key = ai_analysis.get("attentionMapKey")
    if isinstance(object_key, str) and object_key.strip():
        bucket = ai_analysis.get("attentionMapBucket")
        bucket_name = str(bucket).strip() if isinstance(bucket, str) and bucket.strip() else "mri-xai"
        return bucket_name, object_key.strip()

    return None


async def _resolve_mri_subject_id(patient_id: str) -> str:
    row = await db.fetchrow(
        """
        SELECT
            p.subject_id,
            p.user_id,
            (
                SELECT ma.file_path
                FROM mri_assessments ma
                WHERE ma.patient_id = p.user_id
                ORDER BY ma.scan_date DESC NULLS LAST, ma.created_at DESC
                LIMIT 1
            ) AS latest_mri_file_path
        FROM patients p
        WHERE p.subject_id = $1 OR p.user_id::text = $1
        """,
        patient_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")

    row_dict = dict(row)
    explicit_subject_id = row_dict.get("subject_id")
    if explicit_subject_id:
        return str(explicit_subject_id)

    derived_subject_id = _extract_subject_id_from_text(row_dict.get("latest_mri_file_path"))
    if derived_subject_id:
        return derived_subject_id

    return str(row_dict.get("user_id"))


def _convert_dicom_series_to_nifti(dicom_dir: Path, output_path: Path) -> Path:
    # Lazy import so app can still boot even if SimpleITK is unavailable.
    import SimpleITK as sitk

    output_path.parent.mkdir(parents=True, exist_ok=True)
    series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(dicom_dir))
    if not series_ids:
        raise ValueError(f"No DICOM series found in {dicom_dir}")

    def _series_file_count(series_id: str) -> int:
        return len(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(dicom_dir), series_id))

    best_series_id = max(series_ids, key=_series_file_count)
    file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(dicom_dir), best_series_id)
    if not file_names:
        raise ValueError(f"No DICOM files found for series {best_series_id} in {dicom_dir}")

    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(file_names)
    image = reader.Execute()
    # Canonicalize to LPS so middle slice on Z-axis is consistently axial.
    image_lps = sitk.DICOMOrient(image, "LPS")
    sitk.WriteImage(image_lps, str(output_path), True)
    return output_path


def _get_or_build_original_nifti(subject_id: str) -> Optional[Path]:
    dicom_dir = _find_original_dicom_series_dir(subject_id)
    if not dicom_dir:
        return None

    cache_dir = Path(os.getenv("MCI_ORIGINAL_NIFTI_CACHE_DIR", "/tmp/mci-original-nifti"))
    # Versioned cache key to avoid serving previous non-canonical orientation cache.
    cache_path = cache_dir / f"{subject_id}_axial_lps.nii.gz"
    if cache_path.is_file():
        return cache_path

    try:
        return _convert_dicom_series_to_nifti(dicom_dir, cache_path)
    except Exception:
        logger.exception("Failed to convert DICOM to NIfTI for subject_id=%s", subject_id)
        return None


async def _resolve_subject_id(patient_id: str) -> str:
    return await _resolve_mri_subject_id(patient_id)


def _read_nifti_bytes(nii_path: Path) -> bytes:
    if nii_path.suffix == ".gz":
        with gzip.open(nii_path, "rb") as file_obj:
            return file_obj.read()
    return nii_path.read_bytes()


def _parse_nifti_volume_float32(nifti_bytes: bytes):
    # Lazy import so app can still boot even if numpy is unavailable in a non-uv context.
    import numpy as np

    if len(nifti_bytes) < 352:
        raise ValueError("NIfTI file is too small")

    sizeof_hdr_le = struct.unpack("<I", nifti_bytes[0:4])[0]
    sizeof_hdr_be = struct.unpack(">I", nifti_bytes[0:4])[0]
    if sizeof_hdr_le == 348:
        little = True
    elif sizeof_hdr_be == 348:
        little = False
    else:
        raise ValueError("Invalid NIfTI header")

    endian = "<" if little else ">"
    width = struct.unpack(f"{endian}h", nifti_bytes[42:44])[0]
    height = struct.unpack(f"{endian}h", nifti_bytes[44:46])[0]
    depth = struct.unpack(f"{endian}h", nifti_bytes[46:48])[0]
    datatype = struct.unpack(f"{endian}h", nifti_bytes[70:72])[0]
    vox_offset = int(struct.unpack(f"{endian}f", nifti_bytes[108:112])[0])

    if width <= 0 or height <= 0 or depth <= 0:
        raise ValueError("Invalid NIfTI dimensions")
    if vox_offset < 0 or vox_offset >= len(nifti_bytes):
        raise ValueError("Invalid NIfTI voxel offset")

    dtype_map = {
        2: np.dtype(f"{endian}u1"),   # uint8
        256: np.dtype(f"{endian}i1"), # int8
        4: np.dtype(f"{endian}i2"),   # int16
        512: np.dtype(f"{endian}u2"), # uint16
        8: np.dtype(f"{endian}i4"),   # int32
        768: np.dtype(f"{endian}u4"), # uint32
        16: np.dtype(f"{endian}f4"),  # float32
        64: np.dtype(f"{endian}f8"),  # float64
    }
    dtype = dtype_map.get(datatype)
    if dtype is None:
        raise ValueError(f"Unsupported NIfTI datatype: {datatype}")

    voxel_count = width * height * depth
    byte_count = voxel_count * dtype.itemsize
    end = vox_offset + byte_count
    if end > len(nifti_bytes):
        raise ValueError("NIfTI voxel data out of range")

    volume = np.frombuffer(nifti_bytes, dtype=dtype, count=voxel_count, offset=vox_offset)
    return volume.reshape((depth, height, width)).astype(np.float32, copy=False)


def _normalize_slice_float01(slice_2d):
    import numpy as np

    finite = slice_2d[np.isfinite(slice_2d)]
    if finite.size == 0:
        return np.zeros_like(slice_2d, dtype=np.float32)

    low, high = np.percentile(finite, [2.0, 98.0])
    if not np.isfinite(low):
        low = float(finite.min())
    if not np.isfinite(high):
        high = float(finite.max())
    if high <= low:
        high = low + 1.0

    normalized = (slice_2d - low) / (high - low)
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32, copy=False)


def _normalize_slice_uint8(slice_2d):
    import numpy as np

    normalized = _normalize_slice_float01(slice_2d)
    return (normalized * 255.0).astype(np.uint8)


def _extract_middle_slice_uint8(nifti_bytes: bytes):
    volume = _parse_nifti_volume_float32(nifti_bytes)
    return _normalize_slice_uint8(volume[volume.shape[0] // 2])


def _extract_representative_axial_slice_uint8(nifti_bytes: bytes):
    """
    Fallback slice selector when preprocessed reference is unavailable.
    Pick a superior-biased representative axial slice instead of strict middle.
    """
    import numpy as np

    volume = _parse_nifti_volume_float32(nifti_bytes)
    profile = _foreground_profile(volume)
    start, end = _profile_bounds(profile)
    span = max(1, end - start)

    rel_pos = float(os.getenv("MCI_ORIGINAL_SLICE_FALLBACK_REL_POS", "0.62"))
    rel_pos = float(np.clip(rel_pos, 0.0, 1.0))
    idx = int(round(start + (rel_pos * span)))
    idx = int(np.clip(idx, 0, volume.shape[0] - 1))

    logger.info(
        "Fallback original axial slice selected: idx=%s (bounds=%s..%s, rel=%.3f)",
        idx,
        start,
        end,
        rel_pos,
    )
    return _normalize_slice_uint8(volume[idx])


def _resize_nearest(image_2d, out_h: int, out_w: int):
    import numpy as np

    in_h, in_w = image_2d.shape
    if in_h == out_h and in_w == out_w:
        return image_2d

    y_idx = np.linspace(0, in_h - 1, out_h).astype(np.int32)
    x_idx = np.linspace(0, in_w - 1, out_w).astype(np.int32)
    return image_2d[y_idx[:, None], x_idx[None, :]]


def _foreground_profile(volume_3d, threshold: float = 0.12):
    import numpy as np

    depth = volume_3d.shape[0]
    profile = np.zeros(depth, dtype=np.float32)
    for idx in range(depth):
        normalized = _normalize_slice_float01(volume_3d[idx])
        profile[idx] = float((normalized > threshold).sum())
    return profile


def _profile_bounds(profile):
    import numpy as np

    if profile.size == 0:
        return 0, 0

    peak = float(profile.max())
    if peak <= 0.0:
        return 0, int(profile.size - 1)

    threshold = max(64.0, peak * 0.15)
    indices = np.where(profile >= threshold)[0]
    if indices.size == 0:
        indices = np.where(profile > 0)[0]
    if indices.size == 0:
        return 0, int(profile.size - 1)
    return int(indices[0]), int(indices[-1])


def _find_aligned_original_slice_uint8(original_nifti_bytes: bytes, preprocessed_nifti_bytes: bytes):
    """
    Pick an original axial slice aligned to the preprocessed middle-slice position.
    This is more stable than full-volume global correlation for heavily cropped volumes.
    """
    import numpy as np

    original_vol = _parse_nifti_volume_float32(original_nifti_bytes)
    preprocessed_vol = _parse_nifti_volume_float32(preprocessed_nifti_bytes)

    ref_idx = preprocessed_vol.shape[0] // 2
    ref_slice = _normalize_slice_float01(preprocessed_vol[ref_idx])
    ref_slice = np.rot90(ref_slice, 2).copy()
    ref_h, ref_w = ref_slice.shape
    ref_mask = ref_slice > 0.12
    if int(ref_mask.sum()) < 512:
        ref_mask = np.ones((ref_h, ref_w), dtype=bool)

    pre_profile = _foreground_profile(preprocessed_vol)
    pre_start, pre_end = _profile_bounds(pre_profile)
    pre_span = max(1, pre_end - pre_start)
    rel_pos = float(np.clip((ref_idx - pre_start) / pre_span, 0.0, 1.0))

    org_profile = _foreground_profile(original_vol)
    org_start, org_end = _profile_bounds(org_profile)
    org_span = max(1, org_end - org_start)
    target_idx = int(round(org_start + (rel_pos * org_span)))
    # Shift upward (superior) so original slice better aligns with preprocessed presentation.
    superior_bias_ratio = float(os.getenv("MCI_ORIGINAL_SLICE_SUPERIOR_BIAS", "0.085"))
    target_idx += int(round(org_span * superior_bias_ratio))
    target_idx = int(np.clip(target_idx, 0, original_vol.shape[0] - 1))

    lo = max(0, target_idx - 8)
    hi = min(original_vol.shape[0] - 1, target_idx + 8)
    best_idx = target_idx
    best_score = -1e9

    for idx in range(lo, hi + 1):
        candidate = _normalize_slice_float01(original_vol[idx])
        candidate_rs = _resize_nearest(candidate, ref_h, ref_w)

        a = candidate_rs[ref_mask]
        b = ref_slice[ref_mask]
        a_std = float(a.std())
        b_std = float(b.std())
        if a_std < 1e-6 or b_std < 1e-6:
            corr = -1.0
        else:
            corr = float(((a - a.mean()) * (b - b.mean())).mean() / (a_std * b_std + 1e-6))

        # Keep slice close to estimated anatomical position.
        dist_penalty = abs(idx - target_idx) / max(1.0, float(hi - lo))
        score = corr - (0.25 * dist_penalty)

        if score > best_score:
            best_score = score
            best_idx = idx

    logger.info(
        "Aligned original axial slice selected: idx=%s (target=%s, rel=%.3f, bias=%.3f, score=%.4f)",
        best_idx,
        target_idx,
        rel_pos,
        superior_bias_ratio,
        best_score,
    )
    return _normalize_slice_uint8(original_vol[best_idx])


def _fill_border_black_with_gray(image_2d_uint8, threshold: int = 8):
    """
    Fill only border-connected black regions with gray so side bars disappear
    while keeping inner dark anatomy unchanged.
    """
    import numpy as np

    h, w = image_2d_uint8.shape
    if h == 0 or w == 0:
        return image_2d_uint8

    image = image_2d_uint8.copy()
    border_mask = np.zeros((h, w), dtype=bool)
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()

    def try_push(y: int, x: int):
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        if visited[y, x]:
            return
        visited[y, x] = True
        if int(image[y, x]) <= threshold:
            queue.append((y, x))

    for x in range(w):
        try_push(0, x)
        try_push(h - 1, x)
    for y in range(h):
        try_push(y, 0)
        try_push(y, w - 1)

    while queue:
        y, x = queue.popleft()
        border_mask[y, x] = True
        try_push(y - 1, x)
        try_push(y + 1, x)
        try_push(y, x - 1)
        try_push(y, x + 1)

    non_black = image[image > threshold]
    target_gray = int(np.percentile(non_black, 55)) if non_black.size else 160
    target_gray = max(96, min(190, target_gray))
    image[border_mask] = np.uint8(target_gray)
    return image


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack("!I", len(data))
        + chunk_type
        + data
        + struct.pack("!I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _encode_png_gray8(image_2d) -> bytes:
    # Lazy import for symmetry with NIfTI extractor.
    import numpy as np

    if image_2d.ndim != 2:
        raise ValueError("image_2d must be grayscale 2D array")

    height, width = image_2d.shape
    if height <= 0 or width <= 0:
        raise ValueError("Invalid image shape")

    image_2d = np.ascontiguousarray(image_2d, dtype=np.uint8)
    raw_rows = b"".join(b"\x00" + image_2d[y].tobytes() for y in range(height))
    compressed = zlib.compress(raw_rows, level=9)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 0, 0, 0, 0)  # grayscale
    return signature + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", compressed) + _png_chunk(b"IEND", b"")


def _to_gender_label(gender: Optional[int]) -> Optional[str]:
    if gender == 1:
        return "M"
    if gender == 0:
        return "F"
    return None


def _to_age(date_of_birth) -> Optional[int]:
    if not date_of_birth:
        return None
    if not isinstance(date_of_birth, date):
        return None
    today = date.today()
    return (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _format_mmdd(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.strftime("%m-%d")
    if isinstance(value, date):
        return value.strftime("%m-%d")
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # Fallback for string timestamps.
    return text[:10]


def _build_trend_feature(label: str, trend: List[float], unit: str) -> Optional[Dict[str, Any]]:
    cleaned = [float(v) for v in trend if v is not None]
    if not cleaned:
        return None

    def _fmt(value: float) -> str:
        if unit == "%":
            return f"{value:.1f}%"
        return f"{value:.1f} {unit}".strip()

    return {
        "label": label,
        "current": _fmt(cleaned[-1]),
        "baseline": _fmt(cleaned[0]),
        "trend": [round(v, 4) for v in cleaned],
    }


def _to_front_patient_id(row: dict) -> str:
    subject_id = row.get("subject_id")
    if subject_id:
        return str(subject_id)
    return str(row.get("user_id"))


def _build_patient_summary(row: dict) -> dict:
    return {
        "id": _to_front_patient_id(row),
        "rid": row.get("rid"),
        "name": row.get("name"),
        "age": _to_age(row.get("date_of_birth")),
        "gender": _to_gender_label(row.get("gender")),
        "pteducat": row.get("pteducat"),
        "apoe4": row.get("apoe4"),
        "lastVisit": row.get("lastVisit"),
        "examDate": row.get("examDate"),
        "latestViscode2": row.get("latestViscode2"),
        "riskLevel": row.get("risk_level"),
        "cdrSB": row.get("cdrSB"),
        "nxaudito": row.get("nxaudito"),
        "ldelTotal": row.get("ldelTotal"),
        "mmse": row.get("mmse"),
        "moca": row.get("moca"),
        "participationRate": row.get("participation_rate"),
        "diagnosis": "MCI" if (row.get("risk_level") or "").lower() in {"mid", "medium", "high", "suspected", "confirmed"} else "CN",
        "hospital": row.get("hospital"),
    }

@router.get("/patients", response_model=List[PatientWithUser])
async def list_patients(
    doctor_id: int = Query(..., description="Doctor ID for filtering")
):
    """List all patients assigned to this doctor"""
    rows = await db.fetch(
        """
        SELECT p.*, u.name, u.email, u.profile_image_url
        FROM patients p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.doctor_id = $1
        ORDER BY p.created_at DESC
        """,
        doctor_id
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str):
    """Get detailed patient information including clinical trends"""
    # 1. Basic Info (subject_id or user_id both accepted)
    patient = await db.fetchrow(
        """
        SELECT p.*, u.name, u.email, u.profile_image_url, d.hospital
        FROM patients p
        JOIN users u ON p.user_id = u.user_id
        LEFT JOIN doctor d ON p.doctor_id = d.user_id
        WHERE p.subject_id = $1 OR p.user_id::text = $1
        """,
        patient_id
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient_dict = dict(patient)
    user_id = patient_dict["user_id"]

    # 1-1. Doctor's patient list (for frontend patient sheet)
    if patient_dict.get("doctor_id") is not None:
        patient_rows = await db.fetch(
            """
            SELECT
                p.*,
                u.name,
                d.hospital,
                lv.exam_date AS "lastVisit",
                lv.exam_date AS "examDate",
                lv.viscode2 AS "latestViscode2",
                lc.mmse,
                lc.moca,
                lc.cdr_sb AS "cdrSB",
                lc.nxaudito AS "nxaudito",
                ln.avdeltot AS "ldelTotal"
            FROM patients p
            JOIN users u ON p.user_id = u.user_id
            LEFT JOIN doctor d ON p.doctor_id = d.user_id
            LEFT JOIN LATERAL (
                SELECT v.exam_date, v.viscode2
                FROM visits v
                WHERE v.patient_id = p.user_id
                ORDER BY v.exam_date DESC NULLS LAST, v.created_at DESC
                LIMIT 1
            ) lv ON TRUE
            LEFT JOIN LATERAL (
                SELECT ca.mmse, ca.moca, ca.cdr_sb, ca.nxaudito
                FROM clinical_assessments ca
                WHERE ca.patient_id = p.user_id
                ORDER BY ca.exam_date DESC NULLS LAST, ca.created_at DESC
                LIMIT 1
            ) lc ON TRUE
            LEFT JOIN LATERAL (
                SELECT nt.avdeltot
                FROM neuropsych_tests nt
                WHERE nt.patient_id = p.user_id
                ORDER BY nt.exam_date DESC NULLS LAST, nt.created_at DESC
                LIMIT 1
            ) ln ON TRUE
            WHERE p.doctor_id = $1
            ORDER BY p.created_at DESC
            """,
            patient_dict["doctor_id"],
        )
    else:
        patient_rows = [patient]

    patients = [_build_patient_summary(dict(row)) for row in patient_rows]
    current_patient = next(
        (p for p in patients if p["id"] == patient_id or str(p.get("rid")) == patient_id),
        patients[0] if patients else _build_patient_summary(patient_dict),
    )

    latest_clinical_extra = await db.fetchrow(
        """
        SELECT cdr_sb AS "cdrSB", nxaudito
        FROM clinical_assessments
        WHERE patient_id = $1
        ORDER BY exam_date DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        user_id,
    )

    latest_neuro_extra = await db.fetchrow(
        """
        SELECT avdeltot AS "ldelTotal"
        FROM neuropsych_tests
        WHERE patient_id = $1
        ORDER BY exam_date DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        user_id,
    )

    # Ensure current patient always includes key clinical extras even when doctor linkage is absent.
    if current_patient.get("apoe4") is None:
        current_patient["apoe4"] = patient_dict.get("apoe4")
    if latest_clinical_extra:
        latest_clinical_extra_dict = dict(latest_clinical_extra)
        if current_patient.get("cdrSB") is None:
            current_patient["cdrSB"] = latest_clinical_extra_dict.get("cdrSB")
        if current_patient.get("nxaudito") is None:
            current_patient["nxaudito"] = latest_clinical_extra_dict.get("nxaudito")
    else:
        current_patient.setdefault("nxaudito", None)

    if latest_neuro_extra:
        latest_neuro_extra_dict = dict(latest_neuro_extra)
        if current_patient.get("ldelTotal") is None:
            current_patient["ldelTotal"] = latest_neuro_extra_dict.get("ldelTotal")
    else:
        current_patient.setdefault("ldelTotal", None)

    # 2. Clinical Trends (MMSE, MoCA, ADAS, FAQ)
    clinical_rows = await db.fetch(
        """
        SELECT exam_date, viscode2, mmse, moca, adas_cog13, faq
        FROM clinical_assessments
        WHERE patient_id = $1
        ORDER BY exam_date ASC NULLS LAST, created_at ASC
        """,
        user_id
    )

    clinical_trends = {
        "mmse": [],
        "moca": [],
        "adasCog13": [],
        "faq": [],
        "labels": []
    }

    for row in clinical_rows:
        row_dict = dict(row)
        label = row_dict.get("viscode2")
        if label:
            clinical_trends["labels"].append(str(label).upper())
        elif row_dict.get("exam_date"):
            clinical_trends["labels"].append(str(row_dict["exam_date"]))

        if row_dict.get("mmse") is not None:
            clinical_trends["mmse"].append(row_dict["mmse"])
        if row_dict.get("moca") is not None:
            clinical_trends["moca"].append(row_dict["moca"])
        if row_dict.get("adas_cog13") is not None:
            clinical_trends["adasCog13"].append(row_dict["adas_cog13"])
        if row_dict.get("faq") is not None:
            clinical_trends["faq"].append(row_dict["faq"])

    # 3. Biomarkers
    biomarker = await db.fetchrow(
        """
        SELECT
            sample_type,
            abeta42,
            abeta40,
            ptau,
            tau,
            ab42_ab40 AS "ratioAb42Ab40",
            ptau_ab42 AS "ratioPtauAb42",
            ttau_ab42 AS "ratioPtauTau"
        FROM biomarkers
        WHERE patient_id = $1
        ORDER BY collected_date DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        user_id
    )

    biomarker_meta = {
        "platform": "UPENNBIOMK_ROCHE_ELECSYS",
        "kitName": "Roche Elecsys",
        "kitLot": None,
        "datasetName": "All_Subjects_UPENNBIOMK_ROCHE_ELECSYS_23Jan2026.csv",
    }

    # 4. Visits
    visits = await db.fetch(
        """
        SELECT exam_date as "examDate", viscode2 as "viscode2", image_id as "imageId"
        FROM visits
        WHERE patient_id = $1
        ORDER BY exam_date ASC NULLS LAST, created_at ASC
        """,
        user_id
    )

    # 5. MRI Analysis
    mri = await db.fetchrow(
        """
        SELECT
            scan_date as "scanDate",
            classification,
            confidence,
            ai_analysis as "aiAnalysis",
            region_contributions as "regionContributions",
            file_path as "filePath"
        FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY scan_date DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        user_id
    )

    mri_analysis = None
    if mri:
        mri_dict = dict(mri)
        ai_analysis = _as_dict(mri_dict.get("aiAnalysis"))
        db_region_contributions = mri_dict.get("regionContributions")
        if (
            "regionContributions" not in ai_analysis
            and isinstance(db_region_contributions, list)
            and db_region_contributions
        ):
            ai_analysis["regionContributions"] = db_region_contributions
        if "regionContributions" not in ai_analysis:
            ai_analysis["regionContributions"] = [
                {"region": "Hippocampus", "percentage": 35.0, "severity": "high"},
                {"region": "Entorhinal", "percentage": 25.0, "severity": "medium"},
                {"region": "Temporal", "percentage": 15.0, "severity": "medium"},
            ]
        current_front_patient_id = str(current_patient.get("id") or _to_front_patient_id(patient_dict))
        mri_subject_id = (
            str(patient_dict.get("subject_id")).strip()
            if patient_dict.get("subject_id")
            else _extract_subject_id_from_text(mri_dict.get("filePath")) or current_front_patient_id
        )

        if _find_original_dicom_series_dir(mri_subject_id):
            # 원본은 DICOM -> NIfTI 변환본을 사용해서 표시한다.
            ai_analysis["originalImage"] = (
                f"/api/doctor/patients/{current_front_patient_id}/mri/original-slice.png"
                f"?rv={MRI_RENDER_VERSION}"
            )
            ai_analysis["originalNifti"] = (
                f"/api/doctor/patients/{current_front_patient_id}/mri/original-nii"
                f"?rv={MRI_RENDER_VERSION}"
            )

        attention_object = _resolve_attention_map_object(ai_analysis)
        if attention_object:
            ai_analysis["attentionMap"] = (
                f"/api/doctor/patients/{current_front_patient_id}/mri/attention-map.png"
                f"?rv={MRI_RENDER_VERSION}"
            )
        elif _find_preprocessed_nifti(mri_subject_id):
            # CAM이 없을 때 fallback: 전처리본 중간 슬라이스를 노출한다.
            ai_analysis["attentionMap"] = (
                f"/api/doctor/patients/{current_front_patient_id}/mri/preprocessed-slice.png"
                f"?rv={MRI_RENDER_VERSION}"
            )

        mri_analysis = {
            "scanDate": mri_dict.get("scanDate"),
            "classification": mri_dict.get("classification"),
            "confidence": mri_dict.get("confidence"),
            "aiAnalysis": ai_analysis,
        }

    # 6. Voice summary (main report payload)
    recording_rows = await db.fetch(
        """
        SELECT COALESCE(recorded_at, created_at) AS "recordedAt"
        FROM recordings
        WHERE patient_id = $1
        ORDER BY COALESCE(recorded_at, created_at) ASC, created_at ASC
        """,
        user_id,
    )

    voice_rows = await db.fetch(
        """
        SELECT
            COALESCE(va.assessed_at, r.recorded_at, va.created_at, r.created_at) AS "timepoint",
            va.cognitive_score AS "cognitiveScore",
            va.mci_probability AS "mciProbability",
            va.flag AS "flag",
            va.features,
            r.duration_seconds AS "durationSeconds"
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        WHERE r.patient_id = $1
          AND (r.status IS NULL OR r.status = 'completed')
        ORDER BY COALESCE(va.assessed_at, r.recorded_at, va.created_at, r.created_at) ASC,
                 va.created_at ASC
        LIMIT 120
        """,
        user_id,
    )

    upload_counts_by_day: Dict[str, int] = {}
    for row in recording_rows:
        row_dict = dict(row)
        day_label = _format_mmdd(row_dict.get("recordedAt"))
        if not day_label:
            continue
        upload_counts_by_day[day_label] = upload_counts_by_day.get(day_label, 0) + 1

    utterance_trend: List[float] = []
    intensity_trend: List[float] = []
    pause_trend: List[float] = []
    assessed_counts_by_day: Dict[str, int] = {}
    voice_assessment_points: List[Dict[str, Any]] = []

    for row in voice_rows:
        row_dict = dict(row)
        assessed_day_label = _format_mmdd(row_dict.get("timepoint"))
        if assessed_day_label:
            assessed_counts_by_day[assessed_day_label] = assessed_counts_by_day.get(assessed_day_label, 0) + 1

        voice_assessment_points.append(
            {
                "timepoint": row_dict.get("timepoint").isoformat() if row_dict.get("timepoint") else None,
                "cognitiveScore": _as_float(row_dict.get("cognitiveScore")),
                "mciProbability": _as_float(row_dict.get("mciProbability")),
                "flag": (str(row_dict.get("flag") or "").strip().lower() or None),
            }
        )

        features = _as_dict(row_dict.get("features"))
        linguistic_detail = _as_dict(features.get("linguistic_detail"))

        utterance_count = _as_float(linguistic_detail.get("n_par_utts"))
        duration_ms = _as_float(linguistic_detail.get("dur_ms"))
        duration_seconds = _as_float(row_dict.get("durationSeconds"))
        mci_probability = _as_float(row_dict.get("mciProbability"))
        cognitive_score = _as_float(row_dict.get("cognitiveScore"))

        # Fallback for legacy rows without extracted linguistic detail.
        if utterance_count is None and cognitive_score is not None:
            utterance_count = max(cognitive_score / 10.0, 0.0)
        if utterance_count is not None:
            utterance_trend.append(round(utterance_count, 4))

        avg_length_seconds = None
        if duration_ms is not None and utterance_count is not None and utterance_count > 0:
            avg_length_seconds = (duration_ms / 1000.0) / utterance_count
        elif duration_seconds is not None:
            avg_length_seconds = duration_seconds
        if avg_length_seconds is not None:
            intensity_trend.append(round(avg_length_seconds, 4))

        pause_value = _as_float(linguistic_detail.get("filler_rate"))
        if pause_value is not None and pause_value <= 1.0:
            pause_value *= 100.0
        elif pause_value is None and mci_probability is not None:
            pause_value = mci_probability * 100.0
        if pause_value is not None:
            pause_trend.append(round(max(pause_value, 0.0), 4))

    acoustic_features: List[Dict[str, Any]] = []
    for feature in [
        _build_trend_feature("발화 빈도", utterance_trend, "회"),
        _build_trend_feature("음성 강도", intensity_trend, "초"),
        _build_trend_feature("멈춤 빈도", pause_trend, "%"),
    ]:
        if feature:
            acoustic_features.append(feature)

    has_voice_uploads = bool(recording_rows)
    has_voice_data = bool(voice_rows)
    voice_data_status = "ready" if has_voice_data else ("processing" if has_voice_uploads else "none")
    voice_data_days = len(assessed_counts_by_day) if has_voice_data else 0
    latest_voice_assessment = voice_assessment_points[-1] if voice_assessment_points else None
    daily_participation = {
        "labels": list(assessed_counts_by_day.keys()),
        "counts": [assessed_counts_by_day[label] for label in assessed_counts_by_day.keys()],
    }
    daily_uploads = {
        "labels": list(upload_counts_by_day.keys()),
        "counts": [upload_counts_by_day[label] for label in upload_counts_by_day.keys()],
    }

    # Construct response matching frontend expectations
    response = {
        "patients": patients,
        "currentPatient": current_patient,
        "clinicalTrends": clinical_trends,
        "biomarkerResults": dict(biomarker) if biomarker else {},
        "biomarkerMeta": biomarker_meta,
        "visits": [dict(v) for v in visits],
        "dailyParticipation": daily_participation,
        "dailyUploads": daily_uploads,
        "voiceAssessments": voice_assessment_points,
        "latestVoiceAssessment": latest_voice_assessment,
        "acousticFeatures": acoustic_features,
        "mriAnalysis": mri_analysis,
        "dataAvailability": {
            "hasCognitiveTests": bool(clinical_rows),
            "hasMRI": bool(mri),
            "hasBiomarkers": bool(biomarker),
            "hasVoiceUploads": has_voice_uploads,
            "hasVoiceData": has_voice_data,
            "voiceDataStatus": voice_data_status,
            "voiceDataDays": voice_data_days,
        }
    }
    
    return response


@router.get("/patients/{patient_id}/mri/original-nii")
async def get_original_nifti(patient_id: str):
    """Return original MRI as NIfTI bytes (converted from raw DICOM series)."""
    subject_id = await _resolve_subject_id(patient_id)
    nii_path = _get_or_build_original_nifti(subject_id)
    if not nii_path:
        raise HTTPException(status_code=404, detail=f"Original MRI (DICOM) not found for subject_id={subject_id}")

    # Return decompressed NIfTI bytes so frontend does not depend on browser gzip APIs.
    if nii_path.suffix == ".gz":
        try:
            with gzip.open(nii_path, "rb") as file_obj:
                raw_nifti = file_obj.read()
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read NIfTI: {exc}") from exc

        nii_name = nii_path.name[:-3] if nii_path.name.endswith(".gz") else nii_path.name
        return Response(
            content=raw_nifti,
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "public, max-age=300",
                "Content-Disposition": f'inline; filename="{nii_name}"',
            },
        )

    return FileResponse(
        path=str(nii_path),
        media_type="application/gzip",
        filename=nii_path.name,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/patients/{patient_id}/mri/attention-map.png")
async def get_attention_map_png(patient_id: str):
    """Return latest CAM attention map image from ai_analysis, with preprocessed-slice fallback."""
    row = await db.fetchrow(
        """
        SELECT ma.ai_analysis AS "aiAnalysis"
        FROM mri_assessments ma
        JOIN patients p ON p.user_id = ma.patient_id
        WHERE p.subject_id = $1 OR p.user_id::text = $1
        ORDER BY ma.scan_date DESC NULLS LAST, ma.created_at DESC
        LIMIT 1
        """,
        patient_id,
    )

    ai_analysis = _as_dict(dict(row).get("aiAnalysis")) if row else {}
    if ai_analysis:
        resolved = _resolve_attention_map_object(ai_analysis)
        if resolved:
            bucket, key = resolved
            response = None
            try:
                response = storage.client.get_object(bucket, key)
                payload = response.read()
            except Exception as exc:
                logger.warning("Failed to read attention map from MinIO (%s/%s): %s", bucket, key, exc)
            else:
                if payload:
                    return Response(
                        content=payload,
                        media_type="image/png",
                        headers={"Cache-Control": "no-store"},
                    )
            finally:
                if response is not None:
                    response.close()
                    response.release_conn()

    # Fallback for rows without CAM artifacts.
    return await get_preprocessed_nifti_slice_png(patient_id)


@router.get("/patients/{patient_id}/mri/original-slice.png")
async def get_original_nifti_slice_png(patient_id: str):
    """Render a middle axial slice from original MRI (DICOM -> NIfTI) and return PNG bytes."""
    subject_id = await _resolve_subject_id(patient_id)
    nii_path = _get_or_build_original_nifti(subject_id)
    if not nii_path:
        raise HTTPException(status_code=404, detail=f"Original MRI (DICOM) not found for subject_id={subject_id}")

    try:
        raw_original_nifti = _read_nifti_bytes(nii_path)
        preprocessed_path = _find_preprocessed_nifti(subject_id)
        if preprocessed_path:
            raw_preprocessed_nifti = _read_nifti_bytes(preprocessed_path)
            image_2d = _find_aligned_original_slice_uint8(
                raw_original_nifti,
                raw_preprocessed_nifti,
            )
        else:
            image_2d = _extract_representative_axial_slice_uint8(raw_original_nifti)
        png_bytes = _encode_png_gray8(image_2d)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render NIfTI slice: {exc}") from exc

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/patients/{patient_id}/mri/preprocessed-slice.png")
async def get_preprocessed_nifti_slice_png(patient_id: str):
    """Render a middle axial slice from preprocessed NIfTI and return PNG bytes."""
    subject_id = await _resolve_subject_id(patient_id)
    nii_path = _find_preprocessed_nifti(subject_id)
    if not nii_path:
        raise HTTPException(status_code=404, detail=f"Preprocessed NIfTI not found for subject_id={subject_id}")

    try:
        raw_nifti = _read_nifti_bytes(nii_path)
        image_2d = _extract_middle_slice_uint8(raw_nifti)
        # 1) 원본 방향과 맞추기 위해 180도 회전
        # 2) 사이드 빈공간 색칠은 비활성화 (원본 보존)
        import numpy as np

        image_2d = np.rot90(image_2d, 2).copy()
        png_bytes = _encode_png_gray8(image_2d)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render preprocessed NIfTI slice: {exc}") from exc

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/patients", response_model=PatientOut)
async def create_patient(payload: PatientCreate):
    """Create a new patient record"""
    row = await db.fetchrow(
        """
        INSERT INTO patients
        (user_id, date_of_birth, risk_level, doctor_id, notes)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        str(payload.user_id),
        payload.date_of_birth,
        payload.risk_level,
        str(payload.doctor_id) if payload.doctor_id else None,
        payload.notes
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create patient")
    return dict(row)


@router.put("/patients/{patient_id}/risk")
async def update_risk_level(
    patient_id: int,
    risk_level: str = Query(..., description="New Risk Level"),
    doctor_id: str = Query(..., description="Doctor making the update")
):
    """Update patient's Risk Level"""
    result = await db.execute(
        """
        UPDATE patients
        SET risk_level = $1, updated_at = NOW()
        WHERE user_id = $2
        """,
        risk_level,
        str(patient_id)
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Patient not found")

    logger.info(f"Risk level updated for patient {patient_id} by doctor {doctor_id}: {risk_level}")
    return {"status": "ok", "risk_level": risk_level}


@router.post("/patients/{patient_id}/mri/doctor-diagnosis")
async def submit_mri_doctor_diagnosis(
    patient_id: str,
    payload: MRIDoctorDiagnosisPayload,
):
    """Persist doctor-confirmed MRI diagnosis checkboxes as boolean flags."""
    patient = await db.fetchrow(
        """
        SELECT user_id
        FROM patients
        WHERE subject_id = $1 OR user_id::text = $1
        """,
        patient_id,
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    user_id = dict(patient).get("user_id")
    latest_assessment = await db.fetchrow(
        """
        SELECT assessment_id
        FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY scan_date DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        user_id,
    )
    if not latest_assessment:
        raise HTTPException(status_code=404, detail="MRI assessment not found for patient")

    selected = set(payload.diagnoses or [])
    flag_values = {
        db_column: (source_key in selected)
        for source_key, db_column in MRI_DIAGNOSIS_COLUMN_MAP.items()
    }

    diagnosis_summary = {
        "diagnoses": sorted(selected),
        "additionalNotes": (payload.additionalNotes or "").strip(),
        "timestamp": (payload.timestamp or datetime.utcnow()).isoformat(),
        "doctorId": payload.doctorId,
        "confirmed": True,
    }

    updated = await db.fetchrow(
        """
        UPDATE mri_assessments
        SET
            hippocampal_atrophy = $1,
            medial_temporal_atrophy = $2,
            global_brain_volume_decrease = $3,
            white_matter_lesions = $4,
            frontal_atrophy = $5,
            parietal_atrophy = $6,
            doctor_diagnosis = COALESCE(doctor_diagnosis, '{}'::jsonb) || $7::jsonb
        WHERE assessment_id = $8
        RETURNING
            assessment_id,
            hippocampal_atrophy,
            medial_temporal_atrophy,
            global_brain_volume_decrease,
            white_matter_lesions,
            frontal_atrophy,
            parietal_atrophy,
            doctor_diagnosis
        """,
        flag_values["hippocampal_atrophy"],
        flag_values["medial_temporal_atrophy"],
        flag_values["global_brain_volume_decrease"],
        flag_values["white_matter_lesions"],
        flag_values["frontal_atrophy"],
        flag_values["parietal_atrophy"],
        json.dumps(diagnosis_summary),
        dict(latest_assessment).get("assessment_id"),
    )

    return {
        "status": "ok",
        "patient_id": user_id,
        "assessment": dict(updated) if updated else None,
    }


@router.get("/patients/{patient_id}/recordings", response_model=List[RecordingOut])
async def get_recordings(patient_id: int):
    """Get all voice recordings for a patient"""
    rows = await db.fetch(
        """
        SELECT * FROM recordings
        WHERE patient_id = $1
        ORDER BY recorded_at DESC
        LIMIT 100
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}/assessments", response_model=List[VoiceAssessmentOut])
async def get_voice_assessments(patient_id: int):
    """Get all voice assessments for a patient"""
    rows = await db.fetch(
        """
        SELECT va.*
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        WHERE r.patient_id = $1
        ORDER BY va.assessed_at DESC
        LIMIT 100
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}/mri", response_model=List[MRIAssessmentOut])
async def get_mri_results(patient_id: int):
    """Get all MRI assessments for a patient"""
    rows = await db.fetch(
        """
        SELECT * FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY scan_date DESC
        LIMIT 50
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.get("/patients/{patient_id}/progress")
async def get_progress(patient_id: int):
    """Get patient progress over time (voice scores, MRI results)"""
    # Voice assessment scores over time
    voice_scores = await db.fetch(
        """
        SELECT va.assessed_at, va.cognitive_score, va.flag
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        WHERE r.patient_id = $1
        ORDER BY va.assessed_at ASC
        """,
        str(patient_id)
    )

    # MRI classifications over time
    mri_results = await db.fetch(
        """
        SELECT scan_date, classification, confidence
        FROM mri_assessments
        WHERE patient_id = $1
        ORDER BY scan_date ASC
        """,
        str(patient_id)
    )

    return {
        "voice_scores": [dict(r) for r in voice_scores],
        "mri_results": [dict(r) for r in mri_results]
    }


@router.post("/diagnoses", response_model=DiagnosisOut)
async def create_diagnosis(payload: DiagnosisCreate):
    """Create a new diagnosis for a patient"""
    # DEPRECATED
    raise HTTPException(status_code=501, detail="Diagnoses table removed in new schema")


@router.get("/patients/{patient_id}/diagnoses", response_model=List[DiagnosisOut])
async def get_diagnoses(patient_id: int):
    # DEPRECATED
    return []


@router.put("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
async def update_diagnosis(diagnosis_id: UUID, payload: DiagnosisUpdate):
    # DEPRECATED
    raise HTTPException(status_code=501, detail="Diagnoses table removed in new schema")


@router.get("/alerts")
async def list_alerts(doctor_id: str = Query(...)):
    """List all flagged assessments (warning/critical) for this doctor's patients"""
    rows = await db.fetch(
        """
        SELECT va.*, r.patient_id, r.file_path as audio_path, u.name as patient_name
        FROM voice_assessments va
        JOIN recordings r ON va.recording_id = r.recording_id
        JOIN patients p ON r.patient_id = p.user_id
        JOIN users u ON p.user_id = u.user_id
        WHERE p.doctor_id = $1
          AND va.flag IN ('warning', 'critical')
        ORDER BY va.assessed_at DESC
        LIMIT 100
        """,
        doctor_id
    )
    return [dict(r) for r in rows]


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: UUID, doctor_id: str = Query(...)):
    """Mark an alert as reviewed (implemented as adding a note in audit log)"""
    # Check if alert exists
    assessment = await db.fetchrow(
        "SELECT * FROM voice_assessments WHERE assessment_id = $1",
        str(alert_id)
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Log the resolution
    logger.info(f"Alert resolved by doctor {doctor_id} for assessment {alert_id}")
    return {"status": "ok", "message": "Alert marked as reviewed"}


@router.get("/patients/{patient_id}/family", response_model=List[FamilyMemberOut])
async def list_family(patient_id: int):
    """List family members for a patient"""
    rows = await db.fetch(
        """
        SELECT fm.*, u.name, u.email
        FROM caregiver fm
        JOIN users u ON fm.user_id = u.user_id
        WHERE fm.patient_id = $1
        ORDER BY fm.created_at DESC
        """,
        str(patient_id)
    )
    return [dict(r) for r in rows]


@router.post("/patients/{patient_id}/family", response_model=FamilyMemberOut)
async def approve_family(patient_id: int, payload: FamilyMemberCreate, doctor_id: str = Query(...)):
    """Approve family member access to patient data"""
    row = await db.fetchrow(
        """
        INSERT INTO caregiver
        (user_id, patient_id, relationship)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        str(payload.user_id),
        str(patient_id),
        payload.relationship
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to approve family member")

    # TODO: Send notification to family member

    return dict(row)


@router.delete("/patients/{patient_id}/family/{family_id}")
async def remove_family(patient_id: int, family_id: int, doctor_id: str = Query(...)):
    """Remove family member access"""
    result = await db.execute(
        """
        DELETE FROM caregiver
        WHERE user_id = $1 AND patient_id = $2
        """,
        str(family_id),
        str(patient_id)
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Family member not found")

    logger.info(f"Family access removed: {family_id} from patient {patient_id}")
    return {"status": "ok", "message": "Family access removed"}
