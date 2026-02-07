## MCI 인지 평가 플랫폼

RPI 5 + OMV(SATA HAT) 환경에서 동작하는 이중(음성/MRI) 알츠하이머·MCI 진단 플랫폼입니다.

- **음성 ML**: LLM 음성 대화 중 자동 녹음, 1561개 피처 추출(wav2vec2 + BERT + Kiwi), RandomForest 분류
- **MRI ML**: CN/EMCI/LMCI/AD 분류용 계단식 CNN 파이프라인(플레이스홀더)
- **프론트엔드**: Vue 3 + Vite + Pinia, 뉴모피즘 UI, 3개 사용자 역할(환자/보호자/의사)
- **음성 대화**: OpenAI Realtime API 기반 실시간 대화(진행 중)

### 기술 스택

| 레이어 | 기술 |
|-------|-----------|
| Frontend | Vue 3.5, Vite 7, Pinia 3, Vue Router 4 |
| Backend | FastAPI, Python 3.12, UV |
| ML Worker | Celery, faster-whisper (INT8), wav2vec2, BERT, Kiwi, scikit-learn |
| Database | PostgreSQL 16 |
| Storage | MinIO (오디오, MRI 파일) |
| Queue | Redis 7 |
| Proxy | Nginx Alpine |
| Infra | Docker Compose, RPI 5 (8GB), SATA HAT SSDs |

### 프로젝트 구조

```
├── src/claude/
│   ├── app/                    # FastAPI (routers, auth, db, storage)
│   └── worker/                 # Celery ML (feature_extractor, model_inference, tasks)
├── frontend/                   # Vue 3 + Vite
│   └── src/
│       ├── pages/              # 18개 페이지 (Landing, Login, Chat, Doctor 등)
│       ├── components/         # VoiceOrb, WeeklyChart, MRI, shells 등
│       ├── composables/        # useVoiceSession, useAuth, data hooks
│       ├── stores/             # Pinia (auth, doctorPatient)
│       └── data/               # Adapter 패턴 (mock/real API)
├── migrations/001_init.sql     # 데이터베이스 스키마
├── models/audio_processed/     # ML 모델(.pkl)
├── docker/
│   ├── docker-compose.yml
│   └── .env
├── Dockerfile.api              # Python 3.12 + FastAPI
├── Dockerfile.worker           # Python 3.12 + Celery + ML deps
├── nginx.conf
└── pyproject.toml              # UV 설정(Python >=3.11,<3.14)
```

### 서비스

| 컨테이너 | 포트 | 설명 |
|-----------|------|-------------|
| `mci-api` | 8000 | FastAPI 백엔드 (42개 엔드포인트) |
| `mci-worker` | - | Celery ML 워커 (음성/MRI 처리) |
| `mci-postgres` | 5432 | PostgreSQL 16 |
| `mci-minio` | 9000/9001 | MinIO 오브젝트 스토리지 |
| `mci-redis` | 6379 | Redis 작업 큐 |
| `mci-nginx` | 80 | 리버스 프록시 + 프론트 정적 파일 |

### 빠른 시작

```bash
# 1. 환경 변수 설정
cp docker/.env.example docker/.env
# docker/.env를 실제 값으로 수정

# 2. 빌드 및 실행
cd docker
docker compose build --no-cache
docker compose up -d

# 3. 상태 확인
docker ps
docker logs -f mci-worker
```

### 환경 변수 (`docker/.env`)

```
POSTGRES_USER=mci_user
POSTGRES_PASSWORD=change_me
POSTGRES_DB=cognitive

MINIO_USER=minioadmin
MINIO_PASSWORD=change_me

OPENAI_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
JWT_SECRET=change_me
```

### 프론트엔드 개발

```bash
cd frontend
npm install
npm run dev          # Vite 개발 서버 (Node >= 22)
npm run build        # 프로덕션 빌드 → dist/
```

### API 엔드포인트 (총 42개)

- **Auth**: Google OAuth, JWT 로그인/로그아웃, 프로필
- **Doctor**: 환자 관리, 평가 결과, MRI 결과, 진단, 알림, 가족 접근 관리
- **Patient**: WebSocket 음성 대화, 녹음, 평가, 진행도, 프로필
- **Family/Caregiver**: 연결된 환자 데이터, 진행도, 세션
- **Notifications**: CRUD, 미확인 개수, 읽음 처리

### 음성 ML 파이프라인

```
Audio (WebSocket) → MinIO → Celery Worker:
  1. faster-whisper (한국어 STT, INT8)     ~30-60초
  2. wav2vec2 (768차원 오디오 임베딩)      ~20-40초
  3. BERT (768차원 텍스트 임베딩)         ~5-10초
  4. Kiwi (언어학 피처 25개)               ~1-2초
  5. RandomForest 분류                     <1초
  → cognitive_score, mci_probability, flag → DB 저장 + 의사 알림
```

### 사용자 역할

| 역할 | 프론트엔드 role | 접근 권한 |
|------|----------|--------|
| 환자 | `subject` | 음성 대화, 본인 진행도/평가 결과 |
| 가족 | `caregiver` | 연결된 환자 진행도 조회(읽기 전용) |
| 의사 | `doctor` | 전체 환자, 진단, MRI, 알림 |

### 트러블슈팅

```bash
docker ps                           # 컨테이너 상태
docker logs -f mci-api             # API 로그
docker logs -f mci-worker          # Worker 로그
docker exec mci-worker uv pip list # ML 패키지 확인
vcgencmd measure_temp              # RPI 온도 확인
docker stats                       # 리소스 사용량
```

### 아키텍처 문서

상세 30개 섹션 문서는 [MCI_PLATFORM_ARCHITECTURE_RPI5_OMV_DOCKER_UV.md](MCI_PLATFORM_ARCHITECTURE_RPI5_OMV_DOCKER_UV.md) 를 참고하세요.
