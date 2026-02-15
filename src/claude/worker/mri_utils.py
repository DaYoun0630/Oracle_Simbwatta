import os
import glob
import numpy as np
import logging
import urllib.request
from pathlib import Path

try:
    import SimpleITK as sitk
except ImportError:
    sitk = None

try:
    import ants
except ImportError:
    ants = None

try:
    from antspynet.utilities import brain_extraction
except ImportError:
    brain_extraction = None

logger = logging.getLogger(__name__)


def convert_dicom_to_nifti(dicom_folder, save_path):
    """
    DICOM 폴더를 읽어 NIfTI로 변환 후 저장
    """
    if sitk is None:
        raise ImportError("SimpleITK module is not installed.")

    if not os.path.isdir(dicom_folder):
        raise ValueError(f"Not a directory: {dicom_folder}")

    try:
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)

        if not dicom_names:
            raise ValueError(f"No DICOM files found in {dicom_folder}")

        reader.SetFileNames(dicom_names)
        reader.MetaDataDictionaryArrayUpdateOn()
        reader.LoadPrivateTagsOn()
        img = reader.Execute()

        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            sitk.WriteImage(img, save_path)

        return img
    except Exception as e:
        logger.error(f"DICOM conversion error: {e}")
        raise


def _require_ants():
    if ants is None:
        raise ImportError("ANTsPy (antspyx) is required but not installed.")
    if brain_extraction is None:
        raise ImportError("ANTsPyNet is required but not installed.")


def _patch_antspy_compat():
    """Backfill APIs missing in older antspyx versions expected by antspynet."""
    _require_ants()
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


def ensure_antsxnet_assets():
    """
    Pre-download assets needed by ANTsPyNet brain_extraction.
    Uses figshare direct downloader URL to avoid WAF challenge pages.
    """
    _require_ants()
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
        logger.info(f"Downloading ANTsXNet asset: {filename}")
        urllib.request.urlretrieve(url, str(target))
        if target.stat().st_size == 0:
            raise RuntimeError(f"Downloaded empty ANTsXNet asset: {target}")


def _robust_normalize_with_clip(image, clip_range=(-5.0, 5.0)):
    """Robust z-normalization using brain voxels, then clipping."""
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


def preprocess_single_subject_antspy(
    input_path: str,
    output_path: str,
    template_path: str,
    registration_type: str = "SyNRA",
    clip_range: tuple[float, float] = (-5.0, 5.0),
):
    """
    ANTs-based MRI preprocessing:
    1) Read NIfTI
    2) N4 bias correction
    3) Registration to MNI template
    4) ANTsPyNet brain extraction
    5) Robust normalization + clip
    """
    _require_ants()
    _patch_antspy_compat()
    ensure_antsxnet_assets()

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input MRI not found: {input_path}")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"MNI template not found: {template_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    logger.info(f"[ANTs] Loading fixed template: {template_path}")
    fixed_img = ants.image_read(template_path, reorient="RPI")
    logger.info(f"[ANTs] Loading moving image: {input_path}")
    moving_img = ants.image_read(input_path, reorient="RPI")

    logger.info("[ANTs] N4 bias field correction")
    img_n4 = ants.n4_bias_field_correction(moving_img)

    logger.info(f"[ANTs] Registration type={registration_type}")
    tx = ants.registration(fixed=fixed_img, moving=img_n4, type_of_transform=registration_type)
    img_reg = tx["warpedmovout"]

    logger.info("[ANTs] Brain extraction")
    prob_mask = brain_extraction(img_reg, modality="t1", verbose=False)
    brain_mask = ants.threshold_image(prob_mask, low_thresh=0.5, high_thresh=1.0, inval=1, outval=0)
    brain = img_reg * brain_mask

    logger.info("[ANTs] Robust normalization + clip")
    normalized = _robust_normalize_with_clip(brain, clip_range=clip_range)
    ants.image_write(normalized, output_path)
    logger.info(f"[ANTs] Preprocessed MRI saved: {output_path}")
    return output_path


def preprocess_single_subject(input_path, output_path, template_path):
    """
    단일 환자에 대한 전처리 전체 파이프라인
    (Load -> Reorient -> N4 -> Registration -> Skull Strip -> Normalize)
    """
    if sitk is None:
        raise ImportError("SimpleITK module is not installed.")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"MNI Template not found at {template_path}")

    # 1. 이미지 로드
    logger.info(f"Loading image from {input_path}")
    if os.path.isdir(input_path):
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(input_path)
        reader.SetFileNames(dicom_names)
        img = reader.Execute()
    else:
        img = sitk.ReadImage(input_path, sitk.sitkFloat32)

    # float32로 통일
    img = sitk.Cast(img, sitk.sitkFloat32)

    # 2. Reorientation (RPI 표준 방향)
    img = sitk.DICOMOrient(img, "RPI")

    # 3. N4 Bias Field Correction
    logger.info("Running N4 bias field correction...")
    # 마스크 생성 (Otsu 임계값)
    mask = sitk.OtsuThreshold(img, 0, 1, 200)
    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrector.SetMaximumNumberOfIterations([50, 50, 30, 20])
    corrector.SetConvergenceThreshold(1e-6)
    img_n4 = corrector.Execute(img, mask)

    # 4. Template 로드 (MNI152)
    logger.info("Loading MNI152 template...")
    mni_template = sitk.ReadImage(template_path, sitk.sitkFloat32)
    mni_template = sitk.DICOMOrient(mni_template, "RPI")

    # 5. Registration (Affine + BSpline 비선형 정합)
    logger.info("Starting registration (Affine + BSpline)...")
    warped_img = _register_to_template(img_n4, mni_template)

    # 6. Skull Stripping (Template Mask 기반)
    mask_path = template_path.replace(".nii", "_mask.nii").replace(".gz", "")
    if not mask_path.endswith(".nii"):
        mask_path += ".nii"

    if os.path.exists(mask_path):
        logger.info(f"Applying brain mask from {mask_path}")
        mni_mask = sitk.ReadImage(mask_path, sitk.sitkUInt8)
        mni_mask = sitk.DICOMOrient(mni_mask, "RPI")
    else:
        logger.warning(f"Mask not found at {mask_path}, generating via Otsu.")
        mni_mask = sitk.OtsuThreshold(mni_template, 0, 1, 200)

    # 마스크 크기 맞추기 (혹시 다를 경우)
    if mni_mask.GetSize() != warped_img.GetSize():
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(warped_img)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        mni_mask = resampler.Execute(mni_mask)

    masked_img = sitk.Mask(warped_img, mni_mask)

    # 7. Intensity Normalization
    img_array = sitk.GetArrayFromImage(masked_img)

    # Z-score Normalization (배경 0 제외)
    mask_bool = img_array > 0
    if np.any(mask_bool):
        mean_val = np.mean(img_array[mask_bool])
        std_val = np.std(img_array[mask_bool])
        img_array[mask_bool] = (img_array[mask_bool] - mean_val) / (std_val + 1e-8)

    # Clipping (-5, 5) & MinMax Scaling (0~1)
    img_clipped = np.clip(img_array, -5, 5)
    img_final_arr = (img_clipped - img_clipped.min()) / (img_clipped.max() - img_clipped.min() + 1e-8)

    # numpy -> SimpleITK 이미지 (템플릿 메타데이터 유지)
    final_img = sitk.GetImageFromArray(img_final_arr)
    final_img.CopyInformation(mni_template)

    # 8. 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sitk.WriteImage(final_img, output_path)
    logger.info(f"Preprocessed image saved to {output_path}")

    return output_path


def _register_to_template(moving, fixed):
    """
    2단계 정합: Affine(선형) -> BSpline(비선형)
    ANTsPy SyN 대체. RPi5 메모리(8GB) 환경에 최적화.
    BSpline은 2mm 축소 해상도에서 실행 후 원본에 적용.
    """
    import gc

    # --- Stage 1: Affine (전체적 크기/위치/회전 맞춤) ---
    initial_transform = sitk.CenteredTransformInitializer(
        fixed, moving,
        sitk.AffineTransform(3),
        sitk.CenteredTransformInitializerFilter.GEOMETRY
    )

    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    registration.SetMetricSamplingStrategy(registration.RANDOM)
    registration.SetMetricSamplingPercentage(0.20)

    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetOptimizerAsGradientDescent(
        learningRate=1.0,
        numberOfIterations=200,
        convergenceMinimumValue=1e-6,
        convergenceWindowSize=10,
    )
    registration.SetOptimizerScalesFromPhysicalShift()

    registration.SetShrinkFactorsPerLevel([4, 2, 1])
    registration.SetSmoothingSigmasPerLevel([2.0, 1.0, 0.0])
    registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    registration.SetInitialTransform(initial_transform, inPlace=False)
    affine_transform = registration.Execute(fixed, moving)

    logger.info(f"Affine registration done (metric: {registration.GetMetricValue():.4f})")

    # --- Stage 2: BSpline (2mm 축소 해상도에서 실행, 메모리 절약) ---
    # Affine 결과를 축소 해상도로 생성
    shrink = sitk.ShrinkImageFilter()
    shrink.SetShrinkFactors([2, 2, 2])
    fixed_small = shrink.Execute(fixed)

    affine_resampled_small = sitk.Resample(
        moving, fixed_small, affine_transform,
        sitk.sitkLinear, 0.0, moving.GetPixelID()
    )
    gc.collect()

    # 16mm 격자 (축소 이미지 기준, 원본 대비 충분한 비선형 변형)
    grid_physical_spacing = [16.0, 16.0, 16.0]
    image_physical_size = [
        sz * sp for sz, sp in zip(fixed_small.GetSize(), fixed_small.GetSpacing())
    ]
    mesh_size = [
        max(1, int(round(img_sz / grid_sp)))
        for img_sz, grid_sp in zip(image_physical_size, grid_physical_spacing)
    ]

    logger.info(f"BSpline mesh: {mesh_size} on {fixed_small.GetSize()} volume")
    bspline_transform = sitk.BSplineTransformInitializer(fixed_small, mesh_size, order=3)

    registration2 = sitk.ImageRegistrationMethod()
    registration2.SetMetricAsMattesMutualInformation(numberOfHistogramBins=32)
    registration2.SetMetricSamplingStrategy(registration2.RANDOM)
    registration2.SetMetricSamplingPercentage(0.15)

    registration2.SetInterpolator(sitk.sitkLinear)
    registration2.SetOptimizerAsLBFGSB(
        gradientConvergenceTolerance=1e-5,
        numberOfIterations=80,
        maximumNumberOfCorrections=5,
        maximumNumberOfFunctionEvaluations=500,
    )
    registration2.SetInitialTransform(bspline_transform, inPlace=False)

    bspline_result = registration2.Execute(fixed_small, affine_resampled_small)

    logger.info(f"BSpline registration done (metric: {registration2.GetMetricValue():.4f})")

    # 축소 이미지 해제
    del fixed_small, affine_resampled_small
    gc.collect()

    # 최종 결과: Affine + BSpline 결합 → 원본 해상도에 적용
    composite = sitk.CompositeTransform(3)
    composite.AddTransform(affine_transform)
    composite.AddTransform(bspline_result)

    result = sitk.Resample(
        moving, fixed, composite,
        sitk.sitkLinear, 0.0, moving.GetPixelID()
    )

    return result
