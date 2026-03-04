## MCI 인지 평가 플랫폼 (hodu)

Raspberry Pi 5 + Docker Compose 환경에서 동작하는 이중(음성/MRI) 인지 평가 플랫폼입니다.
이 문서는 **현재 `hodu` 프로젝트 상태**를 기준으로 구현 범위, 구성 요소, 실행 방법을 상세 정리합니다.

## 데이터 라이선스 준수 (중요)

이 저장소는 민감한 의료 데이터가 포함될 수 있으므로 다음 원칙을 지킵니다.

- 원본 의료 영상/음성/임상 데이터(원본 DICOM, NIfTI, 음성 파일, 환자 식별 정보)는 README에 기재하지 않습니다.
- 데이터 스크린샷/샘플 파일/외부 업로드 링크를 포함하지 않습니다.
- 실행 예시는 **일반화된 경로/플레이스홀더**만 사용합니다.
- Git에는 코드/설정/합성(synthetic) 예시만 포함하고, 원본/파생 산출물은 커밋하지 않습니다.

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Vue 3, Vite, Pinia, Vue Router |
| Backend API | FastAPI (Python 3.12) |
| Worker | Celery, ANTsPy/ANTsPyNet, PyTorch, CatBoost |
| Queue | Redis |
| Database | PostgreSQL 16 |
| Object Storage | MinIO |
| Infra | Docker Compose, Nginx |

## 서비스 구성 (Docker)

`docker/docker-compose.yml` 기준 서비스:
- `mci-api`: FastAPI 백엔드
- `mci-worker`: Celery 워커 (음성/MRI 파이프라인)
- `mci-postgres`: PostgreSQL 16
- `mci-redis`: Redis
- `mci-minio`: MinIO (오브젝트 스토리지)
- `mci-nginx`: 정적 프론트 + `/api` 프록시

포트 기본값:
- API: `8000`
- Nginx: `80`
- PostgreSQL: `5432`
- MinIO: `9000`(S3), `9001`(콘솔)

## 프로젝트 구조 (실제 `hodu` 기준)

```
hodu/
├── src/
│   ├── app/                 # FastAPI 앱 (라우터/설정/DB/스토리지)
│   │   ├── routers/         # auth, doctor, patient, family, notifications, llm_session, health
│   │   ├── schemas/         # Pydantic 모델
│   │   ├── config.py        # 설정 로더
│   │   ├── db.py            # asyncpg 풀
│   │   └── storage.py       # MinIO 래퍼
│   └── worker/              # Celery 태스크 + ML 파이프라인
│       ├── tasks.py         # process_voice_recording / process_mri_scan
│       ├── feature_extractor.py
│       ├── model_inference.py
│       ├── mri_utils.py / mri_xai.py
│       └── templates/       # MRI 템플릿(표준 공간)
├── frontend/                # Vue 앱 (pages/components/composables)
├── docker/                  # compose + env
├── migrations/              # DB 스키마/마이그레이션
├── scripts/                 # 운영/유틸 스크립트
├── models/                  # 추론 모델 파일
├── data/                    # 로컬 입력 데이터(민감, 커밋 금지)
├── minio-data/              # MinIO 데이터(민감, 커밋 금지)
├── runtime/                 # 런타임 데이터(민감, 커밋 금지)
├── Dockerfile.api / worker
└── nginx.conf
```

## 백엔드 API 구성

`src/app/main.py`에서 등록된 라우터:
- `health`: `/health`, `/health/db`, `/health/minio`, `/health/redis`
- `auth`: 가입/로그인/프로필/설정/토큰
- `doctor`: 환자 요약, MRI 결과, 기록 조회, 진단 저장
- `patient`: 음성 업로드/조회, 프로그레스 조회, 프로필
- `family`: 보호자 조회/프로필
- `notifications`: 알림 조회/읽음 처리
- `llm_session`: LLM 세션 관련 REST

## MRI 파이프라인

**진입점:** `scripts/ingest_mri_folder.py`

처리 흐름:
1. `ingest_mri_folder.py`가 MRI 소스(로컬 경로 또는 MinIO 경로)를 받아 `mri_assessments` 생성
2. Celery `process_mri_scan` 태스크 발행
3. 워커가 ANTs 전처리 → 모델 추론 → 결과 저장
4. 결과는 `mri_assessments` + `mri_files` + MinIO 버킷에 저장

주요 저장소:
- 원본 스캔: MinIO `mri-scans`
- 전처리: MinIO `mri-preprocessed`
- XAI/attention: MinIO `mri-xai`

### MRI 전처리 상세 (ANTs 기반)

`src/worker/mri_utils.py` 기준 전처리 단계:
1. DICOM → NIfTI 변환 (`dcm2niix`)
2. N4 bias correction
3. 템플릿 정합 (기본 `SyNRA`)
4. ANTsPyNet brain extraction
5. 강건 정규화 + 클리핑

템플릿 파일 위치:
- `src/worker/templates/mni_icbm152_t1_tal_nlin_sym_09a.nii`
- `src/worker/templates/mni_icbm152_t1_tal_nlin_sym_09a_mask.nii`

관련 환경변수:
- `MRI_ANTS_REGISTRATION_TYPE` (기본 `SyNRA`)
- `MRI_ANTS_CLIP_MIN`, `MRI_ANTS_CLIP_MAX`
- `MCI_PREPROCESS_CACHE_DIR` 또는 `MCI_PROCESSED_DIR`
- `MCI_PREPROCESSED_BUCKET` (기본 `mri-preprocessed`)

### MRI XAI/ROI 요약

`src/worker/mri_xai.py`에서 Grad-CAM 기반 ROI 점수 및 시각화 결과를 생성합니다.
ROI 사전 정의 및 그룹 집계를 통해 **부위별 기여도 요약**을 생성하며, 결과는 `mri-xai` 버킷에 저장됩니다.

## 음성 파이프라인

**진입점:** `process_voice_recording` (Celery)

처리 흐름:
1. 음성 업로드 후 `recordings` 레코드 생성
2. 워커가 MinIO에서 오디오 + 텍스트(있으면) 로딩
3. 텍스트/음성 피처 추출 → 분류 → 결과 저장
4. 필요 시 알림 생성

핵심 모듈:
- `src/worker/feature_extractor.py`
- `src/worker/model_inference.py`
- `src/worker/transcript_feature_engine.py`

### 음성 피처/모델 상세

`feature_extractor.py`는 **텍스트 기반 경량 추출(Transcript-first)** 경로를 기본으로 사용합니다.
Whisper STT는 워커에서 비활성화되어 있으며(전처리/세션 단계에서 텍스트 제공), 텍스트에서 Kiwi 기반 언어학 피처를 추출합니다.

`model_inference.py`는 두 가지 경로를 지원합니다:
- **Lightweight bundle (권장)**: `redesigned_rf_model_bundle_*.joblib`
- **Legacy 모델**: `trained_model.pkl` + `trained_model_imputer.pkl`

주요 설정:
- `VOICE_MCI_THRESHOLD` (기본 `0.48`)
- `VOICE_MODEL_BUNDLE_PATH`, `VOICE_LEGACY_MODEL_PATH`, `VOICE_LEGACY_IMPUTER_PATH`
- `SHAP_ENABLE`, `SHAP_TOP_K`
- `VOICE_ENABLE_AUDIO_EMBEDDING`, `VOICE_AUDIO_MODEL`, `VOICE_AUDIO_DEVICE`

### 워커 튜닝 (자원/안정성)

`docker/docker-compose.yml` 및 `src/worker/tasks.py` 기준:
- `CELERY_WORKER_CONCURRENCY` (기본 1)
- `CELERY_WORKER_PREFETCH_MULTIPLIER` (기본 1)
- `CELERY_WORKER_MAX_TASKS_PER_CHILD` (기본 5)
- `CELERY_TASK_ACKS_LATE`, `CELERY_TASK_REJECT_ON_WORKER_LOST`
- `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`

저사양 장비에서 과부하를 줄이기 위한 보수적 기본값이 적용되어 있습니다.

## LLM 세션

LLM 세션은 `src/app/llm.py` + `llm_session` 라우터로 구성됩니다.
프론트는 REST 기반으로 세션을 시작/진행/종료하며, 결과는 DB/MinIO에 저장됩니다.

## DB 마이그레이션

`migrations/`에 전체 스키마 및 보조 마이그레이션이 있습니다:
- `004_mci_full_schema.sql`
- `006_insert_dummy_data.sql`
- `007_add_pteducat_to_patients.sql`
- `008_add_shap_to_voice_assessments.sql`
- `009_add_password_hash_to_users.sql`
- `010_convert_mri_diagnosis_flags_to_bool.sql`
- `011_add_mci_subtype_to_patients.sql`

## 스토리지 구조 (MinIO 버킷)

코드에서 사용하는 대표 버킷:
- `voice-recordings`: 음성 파일 업로드
- `voice-transcript`: 음성 텍스트(사이드카)
- `processed`: 일반 처리 결과
- `exports`: 내보내기 결과
- `mri-scans`: 원본 MRI 스캔
- `mri-preprocessed`: 전처리 결과
- `mri-xai`: Grad-CAM/XAI 결과

## 프론트엔드 구조 요약

`frontend/src` 기준:
- `api/`: 백엔드 호출 래퍼
- `components/`: UI 컴포넌트 (의사/환자/보호자 화면 포함)
- `composables/`: 상태/데이터 훅
- `pages/`, `views/`: 라우팅 화면
- `router/`: 라우터 정의
- `stores/`: Pinia 스토어

## 헬스 체크/모니터링

헬스 체크:
- `GET /health`
- `GET /health/db`
- `GET /health/minio`
- `GET /health/redis`

로그 확인:
```bash
docker logs -f mci-api
docker logs -f mci-worker
docker logs -f mci-nginx
```

## 실행 방법

### 1) Docker 실행
```bash
cd docker
docker compose --env-file .env up -d
```

### 2) 프론트 로컬 개발
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```

### 3) 프론트 빌드(nginx용)
```bash
cd frontend
npm run build
```

## 운영 스크립트

`/scripts` 주요 항목:
- `ingest_mri_folder.py`: MRI 파이프라인 트리거
- `preprocess_mri_subject_antspy.py`: 개별 MRI 전처리 테스트
- `apply_migrations.sh`: 마이그레이션 적용
- `copy_voice_pair_from_mch_minio.py`: 음성 데이터 복사 유틸

라이선스 제한 입력 스크립트:
- `import_adni_baseline.py`, `import_adni_baseline_v2.py` (원본 데이터/식별자 노출 금지)

## 시간대 (KST)

워크플로우는 기본적으로 `Asia/Seoul` 기준을 사용합니다.
- 워커 DB 연결: `timezone=Asia/Seoul`
- Celery: `timezone=Asia/Seoul`, `enable_utc=False`

## 환경 변수 (.env)

`docker/.env`에 최소한 아래가 필요합니다.
```bash
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
MINIO_USER=...
MINIO_PASSWORD=...
OPENAI_API_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
JWT_SECRET=...
```

보안:
- 실제 키 값은 README에 포함하지 않습니다.
- `.env`는 Git에 커밋하지 않습니다.

## 주의 사항

- `data/`, `minio-data/`, `runtime/`는 민감 데이터가 포함될 수 있으므로 **커밋 금지**.
- 데이터 경로, 환자 식별자, 원본 파일명은 문서/발표에 기재하지 않습니다.
- 배포 전 `JWT_SECRET`, OAuth, OpenAI 키는 반드시 교체합니다.

## 데이터 사용 및 배포 안전 가이드

- 라이선스 데이터(예: ADNI/TalkBank)는 공개 배포 금지.
- 배포 전 로컬 데이터/MinIO/백업 제거 필요.
- 상세 체크리스트: `COMPLIANCE_CHECKLIST.md`
