#!/usr/bin/env python3
import argparse
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ants
import numpy as np
import SimpleITK as sitk
from antspynet.utilities import brain_extraction

KST = timezone(timedelta(hours=9))


def patch_antspy_compat() -> None:
    """Backfill APIs missing in antspyx 0.4.x that antspynet expects."""
    if hasattr(ants, "one_hot_to_segmentation"):
        return

    def one_hot_to_segmentation(one_hot_array, domain_image, channel_first_ordering=False):
        arr = np.asarray(one_hot_array)
        if arr.ndim not in (3, 4):
            raise ValueError(f"Unexpected one_hot_array shape: {arr.shape}")

        number_of_labels = arr.shape[0] if channel_first_ordering else arr.shape[-1]
        probability_images = []

        for label in range(number_of_labels):
            if domain_image.dimension == 2:
                image_array = arr[label, :, :] if channel_first_ordering else arr[:, :, label]
            else:
                image_array = arr[label, :, :, :] if channel_first_ordering else arr[:, :, :, label]

            probability_images.append(
                ants.from_numpy(
                    np.asarray(image_array, dtype=np.float32),
                    origin=domain_image.origin,
                    spacing=domain_image.spacing,
                    direction=domain_image.direction,
                )
            )

        return probability_images

    ants.one_hot_to_segmentation = one_hot_to_segmentation


def ensure_antsxnet_assets() -> None:
    """
    Pre-download assets that brain_extraction needs.
    ndownloader.figshare.com is used to avoid figshare WAF challenge responses.
    """
    cache_dir = Path.home() / ".keras" / "ANTsXNet"
    cache_dir.mkdir(parents=True, exist_ok=True)

    assets = {
        "brainExtractionRobustT1.h5": "https://ndownloader.figshare.com/files/34821874",
        "S_template3.nii.gz": "https://ndownloader.figshare.com/files/22597175",
    }

    for filename, url in assets.items():
        target = cache_dir / filename
        if target.exists() and target.stat().st_size > 0:
            continue
        urllib.request.urlretrieve(url, str(target))
        if target.stat().st_size == 0:
            raise RuntimeError(f"Downloaded empty asset: {target}")


def find_dicom_series_dirs(subject_root: str) -> list[str]:
    series_dirs = []
    for root, _, files in os.walk(subject_root):
        if any(name.lower().endswith(".dcm") for name in files):
            series_dirs.append(root)
    return sorted(series_dirs)


def dicom_series_to_nifti(series_dir: str, out_nii_gz: str) -> str:
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(series_dir)
    if not dicom_names:
        raise ValueError(f"No DICOM files in series: {series_dir}")
    reader.SetFileNames(dicom_names)
    img = reader.Execute()
    sitk.WriteImage(img, out_nii_gz)
    return out_nii_gz


def robust_normalize_with_clip(image: ants.ANTsImage, clip_range: tuple[float, float]) -> ants.ANTsImage:
    image_np = image.numpy()
    mask = image_np != 0
    brain_pixels = image_np[mask]

    if brain_pixels.size > 0:
        median = np.median(brain_pixels)
        q75, q25 = np.percentile(brain_pixels, [75, 25])
        iqr = q75 - q25
        image_np[mask] = (brain_pixels - median) / (iqr + 1e-7)
        image_np = np.clip(image_np, clip_range[0], clip_range[1])

    return ants.from_numpy(
        image_np,
        origin=image.origin,
        spacing=image.spacing,
        direction=image.direction,
    )


def preprocess_single_nifti(
    nii_path: str,
    template_path: str,
    output_path: str,
    registration_type: str,
    clip_range: tuple[float, float],
) -> None:
    fixed_img = ants.image_read(template_path, reorient="RPI")
    moving_img = ants.image_read(nii_path, reorient="RPI")

    img_n4 = ants.n4_bias_field_correction(moving_img)
    tx = ants.registration(fixed=fixed_img, moving=img_n4, type_of_transform=registration_type)
    img_reg = tx["warpedmovout"]

    prob_mask = brain_extraction(img_reg, modality="t1", verbose=False)
    brain_mask = ants.threshold_image(prob_mask, low_thresh=0.5, high_thresh=1.0, inval=1, outval=0)
    brain = img_reg * brain_mask

    normalized = robust_normalize_with_clip(brain, clip_range=clip_range)
    ants.image_write(normalized, output_path)


def run_subject(
    subject_root: str,
    output_root: str,
    template_path: str,
    registration_type: str,
    clip_range: tuple[float, float],
) -> dict:
    subject_root = os.path.abspath(subject_root)
    output_root = os.path.abspath(output_root)
    template_path = os.path.abspath(template_path)

    if not os.path.isdir(subject_root):
        raise FileNotFoundError(f"Subject folder not found: {subject_root}")
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")

    os.makedirs(output_root, exist_ok=True)
    log_dir = os.path.join(output_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    subject_id = os.path.basename(subject_root.rstrip("/"))
    series_dirs = find_dicom_series_dirs(subject_root)
    if not series_dirs:
        raise RuntimeError(f"No DICOM series found under: {subject_root}")

    results = []
    with tempfile.TemporaryDirectory(prefix=f"tmp_{subject_id}_", dir=output_root) as tmp_dir:
        for idx, series_dir in enumerate(series_dirs, 1):
            series_id = os.path.basename(series_dir.rstrip("/"))
            output_file = os.path.join(output_root, f"{subject_id}_{series_id}_preprocessed.nii.gz")
            temp_nifti = os.path.join(tmp_dir, f"{subject_id}_{series_id}_{idx}.nii.gz")

            result = {
                "subject_id": subject_id,
                "series_dir": series_dir,
                "status": "unknown",
                "output_file": output_file,
                "error_message": None,
            }

            try:
                if os.path.exists(output_file):
                    result["status"] = "skipped"
                else:
                    dicom_series_to_nifti(series_dir, temp_nifti)
                    preprocess_single_nifti(
                        nii_path=temp_nifti,
                        template_path=template_path,
                        output_path=output_file,
                        registration_type=registration_type,
                        clip_range=clip_range,
                    )
                    result["status"] = "success"
            except Exception as exc:
                result["status"] = "failed"
                result["error_message"] = str(exc)

            results.append(result)

    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
    }

    timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "subject_root": subject_root,
        "output_root": output_root,
        "template_path": template_path,
        "registration_type": registration_type,
        "clip_range": clip_range,
        "summary": summary,
        "results": results,
    }
    report_path = os.path.join(log_dir, f"report_{subject_id}_{timestamp}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    report["report_path"] = report_path
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-subject MRI preprocessing with ANTsPy/ANTsPyNet.")
    parser.add_argument(
        "--subject-root",
        default="/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/data/raw/mri/029_S_6726",
    )
    parser.add_argument(
        "--output-root",
        default="/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/minio-data/processed",
    )
    parser.add_argument(
        "--template-path",
        default="/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/src/claude/worker/templates/mni_icbm152_t1_tal_nlin_sym_09a.nii",
    )
    parser.add_argument("--registration-type", default="SyNRA")
    parser.add_argument("--clip-min", type=float, default=-5.0)
    parser.add_argument("--clip-max", type=float, default=5.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clip_range = (args.clip_min, args.clip_max)

    patch_antspy_compat()
    ensure_antsxnet_assets()

    report = run_subject(
        subject_root=args.subject_root,
        output_root=args.output_root,
        template_path=args.template_path,
        registration_type=args.registration_type,
        clip_range=clip_range,
    )

    print(json.dumps(report["summary"], ensure_ascii=False))
    print(report["report_path"])
    if report["summary"]["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
