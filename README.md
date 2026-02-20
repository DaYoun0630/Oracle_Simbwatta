# AD 3D CNN - 2-Stage Inference + ROI Attention

뇌 MRI NIfTI를 대상으로 2단계 분류(CN vs CI, MCI vs AD)와 ROI 기반 CAM/SHAP 시각화를 수행하는 노트북 기반 파이프라인입니다.

CI는 MCI+AD를 의미합니다.

**핵심 파일**
- `test13_cn모델고도화.ipynb`
  CN vs CI (2-class) 학습 노트북. ROI Attention 기반 3D CNN을 학습합니다.
  출력: `13/` 폴더에 `train_split.csv`, `val_split.csv`, `test_split.csv`, `roi_weight_map.png`와 함께 `best_model.pth`/`final_model.pth`가 생성됩니다.
- `test14_ci모델고도화.ipynb`
  MCI vs AD (2-class) 학습 노트북. 출력은 `14/` 폴더에 동일하게 저장됩니다.
- `inference_cam_5.ipynb`
  2-Stage 추론 + CAM/SHAP 시각화 노트북. 최종 결과는 `inference_output5/`에 저장됩니다.

**모델 체크포인트**
- `cn_f189.pth`
  Stage 1 (CN vs CI) 최종 사용 모델.
- `ci_f184.pth`
  Stage 2 (MCI vs AD) 최종 사용 모델.

`inference_cam_5.ipynb`에서 다음 경로로 지정되어야 합니다.

```python
BASE_DIR = Path("/Users/machanho/Desktop/uv/ad")

CN_MODEL_PATH = BASE_DIR / "cn_f189.pth"   # Stage 1: CN vs CI
CI_MODEL_PATH = BASE_DIR / "ci_f184.pth"   # Stage 2: MCI vs AD
DATA_DIR = BASE_DIR / "7.data_mci,ad"
METADATA_PATH = BASE_DIR / "idaSearch_image_download_metadata_2510.csv"
OUTPUT_DIR = BASE_DIR / "inference_output5"
```

**데이터 요구사항**
- `7.data_mci,ad/` 아래에 NIfTI 파일(`.nii`, `.nii.gz`)이 있어야 합니다.
- `idaSearch_image_download_metadata_2510.csv`에 `Subject ID`, `Research Group` 컬럼이 있어야 합니다.
- `Research Group` 값은 `CN`, `MCI`, `AD`만 사용합니다.
- 파일명에서 Subject ID를 추출합니다.
  패턴: `__123_S_4567__` 또는 `123_S_4567`.

**파이프라인 요약**
- Stage 1: CN vs CI 분류.
- Stage 2: MCI vs AD 분류.
- 최종 결과는 `Stage 1`이 CN이면 `CN`, 아니면 `Stage 2` 결과(MCI/AD).
- 입력은 1/99 퍼센타일 기반 정규화 후 `96 x 112 x 96`으로 리사이즈됩니다.
- ROI Attention은 해마(hippocampus), 엔토리날(entorhinal), 해마방회(parahippocampal) 등 지정 ROI에 가우시안 가중치를 적용합니다.

**추론 출력물**
- `inference_output5/all_predictions.csv`
  주요 컬럼: `filename`, `path`, `subject_id`, `true_group`, `s1_pred`, `s1_prob_cn`, `s1_prob_ci`, `s2_pred`, `s2_prob_mci`, `s2_prob_ad`, `final_pred`.
- CAM/SHAP 시각화 PNG
  파일명 규칙: `{subject_id}_{stage_name}_... .png` 형태로 저장됩니다.
  예시: `*_stage1_cn-vs-ci_gradcam_roi_slices.png`, `*_stage2_mci-vs-ad_shap_bar.png`, `*_stage2_mci-vs-ad_shap_cam_roi.png`.

**실행 순서**
1. `test13_cn모델고도화.ipynb` 실행 → `best_model.pth` 생성 후 `cn_f189.pth`로 복사/이동.
2. `test14_ci모델고도화.ipynb` 실행 → `best_model.pth` 생성 후 `ci_f184.pth`로 복사/이동.
3. `inference_cam_5.ipynb`에서 모델 경로 설정 후 전체 추론 및 시각화 실행.

**의존성**
- 필수: `torch`, `numpy`, `pandas`, `nibabel`, `matplotlib`, `scikit-learn`, `tqdm`
- 선택: SHAP 시각화를 위해 `shap`
  설치: `pip install shap`
