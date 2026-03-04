# MCI Platform - Project Summary & Current Status

**Date:** 2026-02-07
**Location:** `/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final`

---

## 📋 Project Overview

**MCI Cognitive Assessment Platform** - Dual-system diagnostic platform for Alzheimer's/cognitive assessment running on Raspberry Pi 5 with local OMV storage (SATA HAT).

### Two Assessment Systems:
1. **Voice-based cognitive training & evaluation**
   - LLM chatbot (GPT-4) for patient training exercises
   - ML model for voice analysis (Whisper, wav2vec2, BERT, Kiwi)
   - Processing time: ~1-2 minutes per recording

2. **MRI-based classification**
   - Cascaded CNN pipeline for CN/EMCI/LMCI/AD classification
   - 3D CNN + CatBoost models
   - Processing time: ~3-7 minutes per scan

---

## 🏗️ Architecture (Target)

### Hardware Setup
- **Compute:** Raspberry Pi 5 (8GB RAM) with active cooling
- **Storage:** Penta SATA HAT with 3 SSDs running OpenMediaVault
- **Network:** Gigabit Ethernet (static IP: 10.0.0.10)
- **All on one node:** No NFS needed, local storage only

### Tech Stack
| Component | Technology | Location |
|-----------|------------|----------|
| **Runtime** | Python 3.10 | Docker containers |
| **Package Manager** | UV | Docker (fast installs) |
| **Containers** | Docker Compose | RPI 5 |
| **Frontend** | Vue.js PWA | Nginx container |
| **API** | FastAPI | Docker container |
| **Background Jobs** | Celery | Docker container |
| **Task Queue** | Redis | Docker container |
| **Database** | PostgreSQL 16 | Docker (data on SATA HAT) |
| **File Storage** | MinIO | Docker (files on SATA HAT) |
| **LLM** | OpenAI API | Cloud (GPT-4) |
| **Voice ML** | Whisper small, wav2vec2, BERT | CPU-optimized |
| **MRI ML** | 3D CNN, CatBoost | CPU-optimized |

### Docker Services Architecture
```
┌─────────────────────────────────────────────┐
│  RPI 5 (Single Node)                        │
│  ┌──────────────────────────────────────┐   │
│  │  nginx (port 80)                     │   │
│  │  ├─ Frontend (Vue.js PWA)            │   │
│  │  └─ API proxy to FastAPI             │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  mci-api (FastAPI)                   │   │
│  │  ├─ REST API endpoints               │   │
│  │  ├─ WebSocket (LLM chat)             │   │
│  │  └─ Google OAuth                     │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  mci-worker (Celery)                 │   │
│  │  ├─ Voice ML pipeline                │   │
│  │  ├─ MRI ML pipeline                  │   │
│  │  └─ Background tasks                 │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  redis (Task queue)                  │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  postgres (Database)                 │   │
│  │  Data: ../postgres-data (SATA HAT)   │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  minio (Object Storage)              │   │
│  │  Data: ../minio-data (SATA HAT)      │   │
│  │  Console: port 9001                  │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 📂 Directory Structure

### Current Structure:
```
/srv/.../final/
├── src/                           ✅ EXISTS
│   ├── gpt/                       ⚠️ Different from architecture plan
│   │   ├── app/
│   │   │   └── main.py           ✅ Basic FastAPI app (health check only)
│   │   └── worker/
│   │       └── tasks.py          ✅ Placeholder Celery worker
│   └── cluade/                    ⚠️ Empty dir (typo?)
├── docker/                        ✅ Complete Docker setup
│   ├── docker-compose.yml        ✅ All 6 services configured
│   ├── .env                      ✅ Environment variables
│   └── Dockerfile                ❓ Extra file
├── frontend/                      ✅ Placeholder
│   └── dist/
│       └── index.html            ⚠️ Empty placeholder
├── migrations/                    ✅ Directory exists
│   └── 000_placeholder.sql       ⚠️ Placeholder only
├── models/                        ✅ Directory exists (empty)
├── postgres-data/                 ✅ Active (PostgreSQL running)
├── minio-data/                    ✅ Active (MinIO running, has system files)
├── .venv/                         ✅ Local Python venv (for development)
├── .git/                          ✅ Git repository initialized
├── pyproject.toml                 ✅ UV package manager config
├── uv.lock                        ✅ UV lock file
├── Dockerfile.api                 ✅ FastAPI container definition
├── Dockerfile.worker              ✅ Celery container definition
├── nginx.conf                     ✅ Nginx routing configuration
├── README.md                      ✅ Basic readme
├── main.py                        ❓ Orphan file
└── MCI_PLATFORM_ARCHITECTURE_RPI5_OMV_DOCKER_UV.md  ✅ Full architecture doc
```

### Target Structure (from architecture):
```
/srv/.../final/
├── code/                          ❌ MISSING (architecture expects this)
│   ├── src/
│   │   ├── api.py                ❌ Not implemented
│   │   ├── tasks.py              ❌ Not implemented
│   │   ├── database.py           ❌ Not implemented
│   │   ├── storage.py            ❌ Not implemented
│   │   ├── auth/                 ❌ Not implemented
│   │   ├── routers/              ❌ Not implemented
│   │   ├── notifications/        ❌ Not implemented
│   │   ├── llm/                  ❌ Not implemented
│   │   └── ml/                   ❌ Not implemented
│   ├── config/                   ❌ Not implemented
│   │   └── prompts/exercises.yaml
│   ├── frontend/
│   ├── migrations/
│   ├── tests/                    ❌ Not implemented
│   └── scripts/                  ❌ Not implemented
└── ...
```

---

## 🔍 Current Implementation Status

### ✅ COMPLETED:

#### 1. Docker Infrastructure (DONE)
- ✅ `docker-compose.yml` with 6 services:
  - postgres (PostgreSQL 16)
  - minio (Object storage)
  - redis (Task queue)
  - api (FastAPI)
  - worker (Celery)
  - nginx (Frontend + proxy)
- ✅ Health checks for all services
- ✅ Service dependencies configured
- ✅ Volume mounts for persistent data
- ✅ Environment variable injection

#### 2. Containerization (DONE)
- ✅ Dockerfile.api - Python 3.10 + UV + FastAPI
- ✅ Dockerfile.worker - Python 3.10 + UV + Celery + ML deps
- ✅ nginx.conf - Frontend serving + API proxy + WebSocket support

#### 3. Package Management (DONE)
- ✅ pyproject.toml with UV configuration
- ✅ uv.lock file generated
- ✅ Dependencies defined:
  - fastapi, uvicorn, celery, redis
  - httpx, pydantic, python-dotenv
  - openai (for GPT-4)

#### 4. Storage Infrastructure (DONE)
- ✅ PostgreSQL data directory (postgres-data/)
- ✅ MinIO data directory (minio-data/) - Active, has .minio.sys/
- ✅ Models directory (models/) - Empty, ready for ML models
- ✅ Local SATA HAT paths configured

#### 5. Basic Application Skeleton (MINIMAL)
- ✅ FastAPI app with /health and / endpoints
- ✅ Celery worker placeholder file
- ⚠️ No actual functionality yet

### ❌ NOT IMPLEMENTED (NEEDS WORK):

#### Phase 1: Database & Core Infrastructure
- ❌ Database schema (12 tables)
  - users, doctors, patients, family_members
  - training_sessions, recordings, voice_assessments, mri_assessments
  - diagnoses, notifications, model_versions, audit_logs
- ❌ Database connection module (asyncpg)
- ❌ MinIO storage service wrapper
- ❌ Environment configuration loader
- ❌ Logging configuration
- ❌ Error handling middleware

#### Phase 2: Authentication (0% Complete)
- ❌ Google OAuth integration
- ❌ JWT token generation/validation
- ❌ User registration flow
- ❌ Login/logout endpoints
- ❌ Session management
- ❌ Permission middleware (Doctor/Patient/Family roles)
- ❌ Auth endpoints (4 total):
  - GET /api/auth/google
  - GET /api/auth/google/callback
  - GET /api/auth/me
  - POST /api/auth/logout

#### Phase 3: API Endpoints (0% Complete)
- ❌ **Doctor Endpoints (12 total):**
  - Patient management (list, view, create, update stage)
  - Recordings & assessments
  - MRI results
  - Diagnoses (create, view, update)
  - Alerts & family management

- ❌ **Patient Endpoints (9 total):**
  - Chat (WebSocket)
  - Exercises
  - Recording upload/list
  - Progress tracking
  - Profile management

- ❌ **Family Endpoints (6 total):**
  - View patient info
  - View progress/assessments
  - View diagnoses

- ❌ **Notification Endpoints (5 total):**
  - List, count, mark read, delete

#### Phase 4: LLM Training System (0% Complete)
- ❌ OpenAI GPT-4 client setup
- ❌ Prompt manager (YAML-based)
  - config/prompts/exercises.yaml
  - word_recall, story_retelling, daily_conversation
  - MCI stage-aware prompts (normal, early_mci, late_mci)
- ❌ Chat service with streaming
- ❌ WebSocket endpoint for real-time chat
- ❌ Training session tracking
- ❌ Conversation history storage (JSONB)

#### Phase 5: Voice ML Pipeline (0% Complete)
- ❌ **Model Integration:**
  - Whisper small (INT8 quantized)
  - wav2vec2-base (Facebook)
  - BERT (klue/bert-base)
  - Kiwi (Korean NLP)
  - Voice classifier model

- ❌ **Pipeline Steps:**
  - Audio preprocessing (librosa)
  - Transcription (Whisper)
  - Audio embeddings (wav2vec2)
  - Text embeddings (BERT)
  - Linguistic features (Kiwi)
  - Feature fusion
  - Classification
  - Flag calculation (normal/warning/critical)

- ❌ **Integration:**
  - Celery task for background processing
  - MinIO download/upload
  - Database result storage
  - Notification triggering

- ❌ **CPU Optimizations:**
  - Thread limits (OMP_NUM_THREADS=4)
  - Singleton pattern for model loading
  - Efficient memory management

#### Phase 6: MRI ML Pipeline (0% Complete)
- ❌ **Preprocessing Pipeline (6 steps):**
  1. DICOM → NIfTI conversion
  2. Denoising (Non-Local Means)
  3. Skull stripping
  4. Centering (center of mass)
  5. Robust-score normalization
  6. Resize to 128×128×128

- ❌ **Classification Models:**
  - Model 1: CN vs Impaired (3D CNN)
  - Model 2: AD vs MCI (3D CNN)
  - Model 3: EMCI vs LMCI (CatBoost)

- ❌ **Cascaded Logic:**
  - Sequential model execution
  - Early termination for CN cases
  - Probability calculation

- ❌ **Integration:**
  - Celery task
  - DICOM file handling (pydicom)
  - Clinical data integration
  - Result storage

#### Phase 7: Notification System (0% Complete)
- ❌ Notification service class
- ❌ Notification types enum
- ❌ Database insert/update logic
- ❌ Badge count calculation
- ❌ Doctor alert triggers (critical flags)
- ❌ Frontend polling endpoint

#### Phase 8: Frontend (0% Complete)
- ❌ Vue.js application setup
- ❌ Three dashboards:
  - Doctor dashboard
  - Patient dashboard
  - Family dashboard
- ❌ Components:
  - LLM chat interface
  - Recording upload UI
  - Progress charts
  - Notification bell 🔔
  - Patient list
  - Assessment viewer
- ❌ PWA configuration
- ❌ Mobile responsiveness
- ❌ Routing (Vue Router)
- ❌ State management (Vuex/Pinia)

#### Phase 9: Testing (0% Complete)
- ❌ Pytest configuration
- ❌ Test fixtures (conftest.py)
- ❌ Unit tests:
  - Auth tests
  - Doctor endpoint tests
  - Patient endpoint tests
  - Notification tests
- ❌ Integration tests:
  - End-to-end API flows
  - ML pipeline tests
- ❌ Test database setup
- ❌ Mock data generation

#### Phase 10: DevOps & Tooling (0% Complete)
- ❌ Backup scripts (PostgreSQL, MinIO)
- ❌ Deployment scripts
- ❌ Database migration system
- ❌ Model versioning tracker
- ❌ Cron jobs for automated backups
- ❌ Monitoring scripts
- ❌ Health check scripts

---

## 📊 Database Schema (12 Tables)

### Core User Tables:
```sql
1. users               -- All users (Google OAuth)
   - id, email, name, google_id, role, profile_picture

2. doctors             -- Doctor profiles
   - id, user_id, hospital, department, license_number

3. patients            -- Patient profiles + MCI stage
   - id, user_id, date_of_birth, mci_stage, assigned_doctor_id

4. family_members      -- Family relationships & permissions
   - id, user_id, patient_id, relationship, permissions
```

### Training & Assessment Tables:
```sql
5. training_sessions   -- LLM chat sessions
   - id, patient_id, exercise_type, conversation (JSONB)

6. recordings          -- Voice audio files
   - id, patient_id, session_id, audio_path, duration, status

7. voice_assessments   -- Voice ML results
   - id, recording_id, transcript, cognitive_score, flag, features (JSONB)

8. mri_assessments     -- MRI ML results
   - id, patient_id, file_path, classification, probabilities (JSONB)

9. diagnoses           -- Doctor's diagnoses
   - id, patient_id, doctor_id, mci_stage, based_on_mri, based_on_voice
```

### System Tables:
```sql
10. notifications      -- In-app notifications
    - id, user_id, type, title, message, is_read

11. model_versions     -- ML model tracking
    - id, model_name, version, file_path, accuracy

12. audit_logs         -- User action logs
    - id, user_id, action, resource_type, resource_id
```

**Status:** ❌ Only placeholder migration exists. No tables created yet.

---

## 🎯 User Roles & Permissions

| Feature | Doctor | Patient | Family |
|---------|--------|---------|--------|
| View all patients | ✅ | ❌ | ❌ |
| View patient details | ✅ (all) | ✅ (own) | ✅ (linked) |
| LLM training chat | ❌ | ✅ | ❌ |
| Upload recordings | ❌ | ✅ | ❌ |
| View voice assessments | ✅ (full) | ✅ (simplified) | ✅ (simplified) |
| View MRI results (raw) | ✅ | ❌ | ❌ |
| Create diagnosis | ✅ | ❌ | ❌ |
| Receive notifications | ✅ (critical) | ✅ (own) | ✅ (linked) |

---

## ⚡ CPU Performance Expectations (RPI 5)

### Processing Times:
| Task | Time | Notes |
|------|------|-------|
| Whisper (small, INT8) | 30-60s | Main bottleneck |
| wav2vec2 embeddings | 20-40s | |
| BERT embeddings | 5-10s | |
| Kiwi features | 1-2s | CPU-native, fast |
| **Voice Total** | **1-2 min** | User: "Processing..." |
| MRI preprocessing | 1-2 min | 6 steps |
| 3D CNN inference | 2-5 min | 2 models |
| CatBoost | <1s | Very fast |
| **MRI Total** | **3-7 min** | User: "Results soon..." |

### CPU Optimization Settings:
```bash
OMP_NUM_THREADS=4
MKL_NUM_THREADS=4
OPENBLAS_NUM_THREADS=4
```

```python
torch.set_num_threads(4)
celery_concurrency=2  # Max 2 workers
```

---

## 🚀 Development Phases (Recommended)

### Phase 1: Foundation (Week 1-2) 🔧
**Goal:** Get database, auth, and basic API working

**Tasks:**
- [ ] Reorganize src/ structure
- [ ] Create all 12 database tables (migrations/001_init.sql)
- [ ] Implement database connection module (src/database.py)
- [ ] Implement MinIO storage service (src/storage.py)
- [ ] Setup logging configuration
- [ ] Basic error handling middleware

**Deliverable:** Can connect to DB and MinIO, tables exist

---

### Phase 2: Authentication (Week 2-3) 🔐
**Goal:** Users can log in with Google

**Tasks:**
- [ ] Google OAuth setup (get client ID/secret)
- [ ] Implement auth/google.py
- [ ] Implement auth/jwt.py
- [ ] Implement auth/permissions.py
- [ ] Create auth router (routers/auth.py)
- [ ] Auth middleware
- [ ] Test with real Google account

**Deliverable:** Working login/logout with Google OAuth

---

### Phase 3: Basic API Endpoints (Week 3-4) 🌐
**Goal:** Doctors and patients can see data

**Tasks:**
- [ ] Implement routers/doctor.py (12 endpoints)
- [ ] Implement routers/patient.py (9 endpoints)
- [ ] Implement routers/family.py (6 endpoints)
- [ ] Add permission checks to all endpoints
- [ ] Write API tests
- [ ] Test with Postman/curl

**Deliverable:** Full REST API with auth

---

### Phase 4: LLM Training System (Week 4-5) 🤖
**Goal:** Patients can chat with AI for training

**Tasks:**
- [ ] Get OpenAI API key
- [ ] Create config/prompts/exercises.yaml
- [ ] Implement llm/prompt_manager.py
- [ ] Implement llm/chat_service.py
- [ ] Create WebSocket endpoint (/api/patient/chat)
- [ ] Store training sessions in database
- [ ] Test different exercise types

**Deliverable:** Working AI chat for cognitive training

---

### Phase 5: Voice ML Pipeline (Week 5-7) 🎤
**Goal:** Voice recordings are analyzed automatically

**Tasks:**
- [ ] Download/prepare ML models:
  - Whisper small (HuggingFace)
  - wav2vec2-base (HuggingFace)
  - klue/bert-base (HuggingFace)
  - Kiwi (pip install)
  - voice_classifier.pt (train or mock)
- [ ] Implement ml/voice_pipeline.py
- [ ] Implement Celery task (tasks.process_voice_recording)
- [ ] Create recording upload endpoint
- [ ] Test with sample Korean audio
- [ ] Optimize for RPI 5 CPU

**Deliverable:** Voice analysis working end-to-end

---

### Phase 6: MRI ML Pipeline (Week 7-9) 🧠
**Goal:** MRI scans are classified automatically

**Tasks:**
- [ ] Get sample MRI DICOM files (ADNI or mock)
- [ ] Implement ml/mri_pipeline.py (preprocessing)
- [ ] Download/prepare 3D CNN models (or mock)
- [ ] Download/prepare CatBoost model (or mock)
- [ ] Implement Celery task (tasks.process_mri_scan)
- [ ] Create MRI upload endpoint
- [ ] Test with sample scans

**Deliverable:** MRI classification working

---

### Phase 7: Notifications (Week 9-10) 🔔
**Goal:** Users get notified about important events

**Tasks:**
- [ ] Implement notifications/service.py
- [ ] Implement notifications router (5 endpoints)
- [ ] Add notification triggers (flags, new diagnoses)
- [ ] Test notification creation
- [ ] Test badge count

**Deliverable:** In-app notification system working

---

### Phase 8: Frontend (Week 10-12) 🎨
**Goal:** Beautiful, usable web interface

**Tasks:**
- [ ] Setup Vue.js project (Vite)
- [ ] Create 3 dashboards (Doctor, Patient, Family)
- [ ] Implement components:
  - Login page
  - Patient list
  - LLM chat interface
  - Recording upload
  - Progress charts
  - Notification bell
- [ ] Setup Vue Router
- [ ] Setup Pinia (state management)
- [ ] PWA configuration
- [ ] Build and deploy to nginx

**Deliverable:** Full web interface

---

### Phase 9: Testing & Polish (Week 12-13) ✅
**Goal:** Production-ready quality

**Tasks:**
- [ ] Write comprehensive tests (pytest)
- [ ] Load testing (simulate 10+ concurrent users)
- [ ] Fix bugs
- [ ] Optimize performance
- [ ] Add error messages
- [ ] Documentation

**Deliverable:** Stable, tested application

---

### Phase 10: Deployment & Operations (Week 13-14) 🚀
**Goal:** Deployed and running 24/7

**Tasks:**
- [ ] Setup backup scripts (cron)
- [ ] Setup monitoring
- [ ] Configure static IP on RPI
- [ ] SSL/HTTPS setup (Let's Encrypt)
- [ ] User training documentation
- [ ] Deployment runbook

**Deliverable:** Production deployment

---

## ⚠️ Critical Issues & Blockers

### 1. Source Code Structure Mismatch 🔴
**Problem:** Architecture doc expects `code/src/` but we have `src/gpt/`

**Impact:** Confusion, harder to follow architecture

**Solution Options:**
- A) Restructure to `code/src/api.py`, `code/src/routers/`, etc.
- B) Update architecture doc to match current structure
- C) Hybrid: Keep `src/` at root, add proper subdirectories

**Recommendation:** Option A (restructure to match architecture)

---

### 2. Missing ML Models 🔴
**Problem:** models/ directory is empty. No .pt or .cbm files.

**Impact:** Can't test ML pipelines

**Solution Options:**
- A) Train from scratch (requires ADNI dataset, weeks of work)
- B) Use placeholder/mock models for development
- C) Download pre-trained public models as substitutes

**Recommendation:** Option B for Phase 1-4, Option A/C for Phase 5-6

---

### 3. External Service Setup Required 🟡
**Problem:** Need accounts/credentials for:
- OpenAI API (GPT-4)
- Google Cloud (OAuth)

**Impact:** Can't test LLM or auth without these

**Solution:**
- [ ] Create OpenAI account, get API key (~$20 credit)
- [ ] Setup Google Cloud project, create OAuth app
- [ ] Add credentials to docker/.env

**Estimated Cost:** $0-50/month (OpenAI usage-based)

---

### 4. Network Configuration 🟡
**Problem:** Architecture assumes static IP 10.0.0.10 for RPI

**Impact:** Networking issues if IP changes

**Solution:**
- [ ] Configure router to assign static IP to RPI MAC address
- [ ] OR use mDNS (rpi5.local)
- [ ] OR update architecture to use dynamic DNS

---

### 5. Frontend Framework Not Initialized 🟡
**Problem:** frontend/dist/ only has empty index.html

**Impact:** No UI to test backend features

**Solution Options:**
- A) Build Vue.js app (as per architecture)
- B) Build simple React app
- C) Use Postman/curl for Phase 1-7, build UI in Phase 8

**Recommendation:** Option C (defer frontend until backend works)

---

## 📝 Quick Commands Reference

### Docker Operations:
```bash
# Navigate to project
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final

# Start all services
cd docker && docker compose up -d

# Check status
docker ps

# View logs
docker logs -f mci-api
docker logs -f mci-worker
docker logs -f mci-postgres

# Rebuild after code changes
docker compose build api worker
docker compose up -d

# Stop all services
docker compose down

# Full cleanup (⚠️ DELETES DATA)
docker compose down -v --rmi all

# Execute commands in containers
docker exec -it mci-api bash
docker exec -it mci-postgres psql -U mci_user -d cognitive

# Check resource usage
docker stats
```

### Development Workflow:
```bash
# 1. Edit code in src/
vim src/gpt/app/main.py

# 2. Rebuild container
cd docker && docker compose build api

# 3. Restart service
docker compose up -d api

# 4. Test
curl http://localhost/health
curl http://localhost/api/

# 5. Check logs
docker logs -f mci-api
```

### Database Operations:
```bash
# Connect to PostgreSQL
docker exec -it mci-postgres psql -U mci_user -d cognitive

# Backup database
docker exec mci-postgres pg_dump -U mci_user cognitive > backup.sql

# Restore database
docker exec -i mci-postgres psql -U mci_user -d cognitive < backup.sql

# Run migration
docker exec -i mci-postgres psql -U mci_user -d cognitive < migrations/001_init.sql
```

### MinIO Operations:
```bash
# Access MinIO Console
# Browser: http://localhost:9001
# Login: minioadmin / <password from .env>

# MinIO CLI (if installed)
mc alias set local http://localhost:9000 minioadmin <password>
mc ls local/
mc mb local/voice-recordings
```

### UV Package Management:
```bash
# Add new dependency
uv add fastapi

# Remove dependency
uv remove package-name

# Sync dependencies
uv sync

# Run command in UV environment
uv run python script.py
uv run pytest
```

---

## 🔗 Access Points

Once services are running:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost or http://10.0.0.10 | N/A |
| API Health | http://localhost/api/health | N/A |
| MinIO Console | http://localhost:9001 | minioadmin / (from .env) |
| PostgreSQL | localhost:5432 | mci_user / (from .env) |
| Redis | localhost:6379 | No auth |

From inside Docker network:
- PostgreSQL: `postgres:5432`
- Redis: `redis:6379`
- MinIO: `minio:9000`
- API: `api:8000`

---

## 📚 Key Files to Know

### Configuration:
- `docker/docker-compose.yml` - All service definitions
- `docker/.env` - Environment variables (SECRETS!)
- `pyproject.toml` - Python dependencies (UV)
- `nginx.conf` - Web server routing

### Application:
- `src/gpt/app/main.py` - FastAPI application (NEEDS EXPANSION)
- `src/gpt/worker/tasks.py` - Celery tasks (NEEDS IMPLEMENTATION)
- `migrations/` - Database schema changes

### Docker:
- `Dockerfile.api` - API container build
- `Dockerfile.worker` - Worker container build

### Documentation:
- `MCI_PLATFORM_ARCHITECTURE_RPI5_OMV_DOCKER_UV.md` - Full architecture (62KB)
- `README.md` - Basic project info

---

## 🎯 Immediate Next Steps (Choose One)

### Option A: Start Development Properly ⭐ RECOMMENDED
1. Create proper `src/` structure matching architecture
2. Implement database schema (migrations/001_init.sql)
3. Build database.py (asyncpg connection)
4. Build storage.py (MinIO wrapper)
5. Test database + storage connection

**Why:** Builds solid foundation for everything else

---

### Option B: Quick Prototype
1. Keep current structure
2. Add one simple endpoint (e.g., list patients - mock data)
3. Test Docker rebuild/restart workflow
4. Add basic frontend page

**Why:** Validates Docker setup works

---

### Option C: Focus on Infrastructure First
1. Setup Google OAuth (get credentials)
2. Setup OpenAI API (get key)
3. Document environment setup
4. Update docker/.env with real values
5. Test external service connectivity

**Why:** Removes blockers for future phases

---

## 💡 Key Architecture Insights

### What Makes This Special:
1. **Single-node design** - Everything on one RPI, no NFS complexity
2. **UV package manager** - 10-100x faster than pip
3. **CPU-optimized ML** - INT8 quantization, thread limits
4. **Docker isolation** - No Python pollution on host
5. **Local storage** - SATA HAT eliminates network latency
6. **Modular design** - Can add/remove features easily

### Performance Characteristics:
- **Voice processing:** 1-2 minutes (acceptable for clinic use)
- **MRI processing:** 3-7 minutes (batch processing overnight OK)
- **Storage capacity:** 1TB = ~10,000 voice or ~500 MRI scans
- **Concurrent users:** ~5-10 (RPI 5 CPU limit)
- **Best for:** Small clinic, research, prototype

### Technology Choices Explained:
- **PostgreSQL vs MySQL:** Better JSONB support (for features/conversation)
- **MinIO vs S3:** Self-hosted, no cloud costs, S3-compatible API
- **Redis vs RabbitMQ:** Simpler, faster, sufficient for use case
- **FastAPI vs Flask:** Better async support, auto-docs, type hints
- **Celery vs RQ:** More mature, better monitoring, supports complex workflows
- **Vue vs React:** Lighter, easier learning curve (debatable!)

---

## 📊 Estimated Work Breakdown

| Phase | Difficulty | Time | Priority |
|-------|-----------|------|----------|
| Database Schema | Easy | 1 day | 🔴 Critical |
| Database Module | Easy | 1 day | 🔴 Critical |
| MinIO Module | Easy | 1 day | 🔴 Critical |
| Google OAuth | Medium | 2-3 days | 🔴 Critical |
| JWT Auth | Medium | 2 days | 🔴 Critical |
| Doctor API | Medium | 3 days | 🟡 High |
| Patient API | Medium | 3 days | 🟡 High |
| Family API | Easy | 1 day | 🟢 Medium |
| LLM Chat | Medium | 3-4 days | 🟡 High |
| Voice Pipeline | Hard | 5-7 days | 🟡 High |
| MRI Pipeline | Hard | 5-7 days | 🟢 Medium |
| Notifications | Easy | 2 days | 🟢 Medium |
| Frontend (Vue) | Hard | 7-10 days | 🟢 Medium |
| Testing | Medium | 3-5 days | 🟢 Medium |
| Deployment | Easy | 2 days | 🟢 Low |

**Total Estimated Time:** 8-12 weeks (full-time)

---

## 🔥 Common Gotchas & Tips

### Docker:
- ⚠️ Always `docker compose build` after changing Dockerfile
- ⚠️ Always `docker compose up -d` after changing docker-compose.yml
- ⚠️ Check logs first when things break: `docker logs -f <service>`
- 💡 Use `docker compose down -v` to reset database (loses data!)
- 💡 `docker compose exec api bash` to debug inside container

### UV:
- ⚠️ Run `uv lock` after editing pyproject.toml
- ⚠️ Commit uv.lock to git (like package-lock.json)
- 💡 UV caches downloads - much faster on rebuild

### PostgreSQL:
- ⚠️ Data persists in postgres-data/ even after `docker compose down`
- ⚠️ Password in .env must match on first run
- 💡 Use asyncpg (async) not psycopg2 (sync)

### MinIO:
- ⚠️ Buckets must be created before use
- ⚠️ Use MINIO_ENDPOINT without http:// in Python code
- 💡 MinIO Console at :9001 is super helpful for debugging

### RPI 5:
- ⚠️ Monitor temperature: `vcgencmd measure_temp`
- ⚠️ Keep below 80°C to avoid throttling
- 💡 Active cooling essential for ML workloads
- 💡 Set thread limits or RPI will freeze

---

## 📞 Support & Resources

### Documentation:
- FastAPI Docs: https://fastapi.tiangolo.com
- Celery Docs: https://docs.celeryproject.org
- UV Docs: https://github.com/astral-sh/uv
- MinIO Docs: https://min.io/docs/minio/linux/index.html
- PostgreSQL Docs: https://www.postgresql.org/docs/

### Debugging:
1. Check Docker logs first
2. Check environment variables
3. Check network connectivity (ping, curl)
4. Check disk space (df -h)
5. Check RPI temperature

### Getting Help:
- Architecture questions → Review architecture doc
- Docker issues → Check docker logs
- Python errors → Check container with `docker exec`
- API errors → Check FastAPI auto-docs at /docs

---

**End of Summary**

Generated: 2026-02-07
Location: ~/claude/PROJECT_SUMMARY.md
Project: MCI Platform
Status: Initial skeleton, 95% not implemented
Next: Choose Phase 1 approach and start building!
