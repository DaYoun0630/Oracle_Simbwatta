# MCI Cognitive Assessment Platform - RPI 5 + OMV (SATA HAT, Docker + UV)

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Hardware Setup](#4-hardware-setup)
5. [CPU Performance Expectations](#5-cpu-performance-expectations)
6. [Directory Structure](#6-directory-structure)
7. [User Roles & Permissions](#7-user-roles--permissions)
8. [Database Schema](#8-database-schema)
9. [API Endpoints](#9-api-endpoints)
10. [Authentication (Google OAuth)](#10-authentication-google-oauth)
11. [OMV Storage Setup (Local SATA HAT)](#11-omv-storage-setup-local-sata-hat)
12. [RPI 5 Setup](#12-rpi-5-setup)
13. [Docker Configuration](#13-docker-configuration)
14. [UV Package Management](#14-uv-package-management)
15. [File Storage (MinIO)](#15-file-storage-minio)
16. [LLM Training System](#16-llm-training-system)
17. [Voice ML Pipeline (CPU-Optimized)](#17-voice-ml-pipeline-cpu-optimized)
18. [MRI ML Pipeline (CPU-Optimized)](#18-mri-ml-pipeline-cpu-optimized)
19. [Celery Background Tasks](#19-celery-background-tasks)
20. [Model Versioning](#20-model-versioning)
21. [In-App Notification System](#21-in-app-notification-system)
22. [Logging & Monitoring](#22-logging--monitoring)
23. [Backup Strategy](#23-backup-strategy)
24. [Testing Guide](#24-testing-guide)
25. [Deployment](#25-deployment)
26. [Mobile App Considerations](#26-mobile-app-considerations)
27. [Environment Variables](#27-environment-variables)
28. [Development Phases](#28-development-phases)
29. [Troubleshooting](#29-troubleshooting)

---

## 1. Project Overview

A dual-system diagnostic platform for Alzheimer's/cognitive assessment:

1. **Voice-based cognitive training & evaluation**
   - LLM chatbot for patient training
   - ML model for voice analysis
   
2. **MRI-based classification**
   - Cascaded CNN pipeline for CN/EMCI/LMCI/AD classification

**This Version Features:**
- ✅ Docker containers (clean, isolated)
- ✅ UV package manager (fast installs)
- ✅ Python 3.10
- ✅ RPI 5 for compute (ML processing)
- ✅ OMV storage on RPI (SATA HAT) for database/files
- ✅ CPU-optimized ML pipelines
- ✅ In-app notifications
- ✅ No Python installed on host systems

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 RPI 5 + OMV (SATA HAT) + DOCKER + UV                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                    RPI 5 (Compute + Storage)                         │  │
│   │                                                                      │  │
│   │   Docker Containers:                                                 │  │
│   │   ┌───────────────────┐   ┌───────────────────┐   ┌────────────────┐ │  │
│   │   │ Nginx             │   │ FastAPI + UV      │   │ Celery + UV    │ │  │
│   │   │ (static files)    │   │ (API)             │   │ (ML workers)   │ │  │
│   │   └───────────────────┘   └───────────────────┘   └────────────────┘ │  │
│   │   ┌───────────────────┐   ┌───────────────────┐   ┌────────────────┐ │  │
│   │   │ Redis             │   │ PostgreSQL        │   │ MinIO          │ │  │
│   │   │ (task queue)      │   │ (database)        │   │ (file storage) │ │  │
│   │   └───────────────────┘   └───────────────────┘   └────────────────┘ │  │
│   │                                                                      │  │
│   │   Local Volumes (SATA HAT SSDs):                                     │  │
│   │   • code/ • models/ • postgres-data/ • minio-data/ • backups/        │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│   Host: Only Docker (no Python on host) ✅                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Component | Technology | Location | Notes |
|-----------|------------|----------|-------|
| **Runtime** | Python 3.10 | Inside Docker | Not on host |
| **Package Manager** | UV | Inside Docker | Fast installs |
| **Containers** | Docker + Compose | RPI 5 | Isolated |
| **Frontend** | Vue.js + PWA | RPI 5 (Nginx) | |
| **API** | FastAPI | RPI 5 (Docker) | |
| **Background Jobs** | Celery | RPI 5 (Docker) | ML processing |
| **Task Queue** | Redis | RPI 5 (Docker) | Low latency |
| **Database** | PostgreSQL | RPI 5 (Docker) | Local SSD |
| **File Storage** | MinIO | RPI 5 (Docker) | Audio, MRI |
| **LLM** | OpenAI API | Cloud | GPT-4 |
| **Voice ML** | Whisper small, wav2vec2, BERT | RPI 5 | CPU-optimized |
| **MRI ML** | 3D CNN, CatBoost | RPI 5 | CPU-optimized |

---

## 4. Hardware Setup

### Your Setup ✅

| Component | Details | Status |
|-----------|---------|--------|
| **RPI 5** | 8GB RAM | ✅ |
| **Cooling** | Active (fan) | ✅ |
| **Storage** | Penta SATA HAT (3 SSDs, OMV local) | ✅ |
| **Network** | Gigabit Ethernet | ✅ |

### Network Configuration

```
┌──────────────┐
│    RPI 5     │ 10.0.0.10
└─────┬────────┘
      │
┌─────▼──────┐
│   Router  │ 10.0.0.1
└───────────┘
```

Use a static IP for reliability.

---

## 5. CPU Performance Expectations

### Processing Times (RPI 5)

| Task | Time | Notes |
|------|------|-------|
| Whisper (small, INT8) | ~30-60 sec | Main bottleneck |
| wav2vec2 | ~20-40 sec | |
| BERT | ~5-10 sec | |
| Kiwi | ~1-2 sec | CPU-native, fast |
| 3D CNN (MRI) | ~2-5 min | |
| CatBoost | <1 sec | CPU-native, fast |

### Total Pipeline Times

| Pipeline | Time | User Experience |
|----------|------|-----------------|
| **Voice Analysis** | ~1-2 min | "Processing your recording..." |
| **MRI Classification** | ~3-7 min | "Results will be ready soon..." |

---

## 6. Directory Structure

```
RPI 5 (OMV local storage): /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/
│
├── code/                              ← Git repository
│   ├── src/
│   │   ├── __init__.py
│   │   ├── api.py                     ← FastAPI app
│   │   ├── tasks.py                   ← Celery tasks
│   │   ├── database.py
│   │   ├── storage.py
│   │   ├── auth/
│   │   │   ├── google.py
│   │   │   ├── jwt.py
│   │   │   └── permissions.py
│   │   ├── routers/
│   │   │   ├── doctor.py
│   │   │   ├── patient.py
│   │   │   ├── family.py
│   │   │   └── notifications.py
│   │   ├── notifications/
│   │   │   ├── types.py
│   │   │   └── service.py
│   │   ├── llm/
│   │   │   ├── prompt_manager.py
│   │   │   └── chat_service.py
│   │   └── ml/
│   │       ├── voice_pipeline.py
│   │       └── mri_pipeline.py
│   │
│   ├── config/
│   │   ├── prompts/
│   │   │   └── exercises.yaml
│   │   └── models.yaml
│   │
│   ├── frontend/
│   │   ├── src/
│   │   ├── dist/                      ← Built files
│   │   └── package.json
│   │
│   ├── migrations/
│   │   └── 001_init.sql
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_doctor.py
│   │   └── test_notifications.py
│   │
│   ├── scripts/
│   │   ├── backup.sh
│   │   └── deploy.sh
│   │
│   ├── pyproject.toml                 ← UV config
│   ├── uv.lock                        ← UV lock file
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── nginx.conf
│   └── .env.example
│
├── docker/
│   ├── docker-compose.yml             ← Unified single-node (recommended)
│   ├── docker-compose.nas.yml         ← Storage-only (optional)
│   └── .env                           ← Shared env vars
│
├── models/                            ← ML model files
│   ├── voice_classifier.pt
│   ├── mri_model1.pt
│   ├── mri_model2.pt
│   └── catboost_subtype.cbm
│
├── postgres-data/                     ← PostgreSQL data (auto-created)
│
├── minio-data/                        ← MinIO storage
│   ├── voice-recordings/
│   ├── mri-scans/
│   └── processed/
│
└── backups/                           ← Automated backups
    ├── postgres/
    └── minio/


Local Storage:
Use the OMV local path directly (no /mnt/nas mount).

Host system (RPI 5):
- Only Docker installed
- No Python on host
- No venv on host
- Everything runs in containers
```

---

## 7. User Roles & Permissions

### Three User Roles

| Role | Description | Primary Functions |
|------|-------------|-------------------|
| **Doctor** | Medical professional | Diagnose, view all data, manage patients |
| **Patient** | Person receiving care | Training sessions, view own progress |
| **Family** | Patient's family member | View linked patient's progress (read-only) |

### Permission Matrix

| Feature | Doctor | Patient | Family |
|---------|--------|---------|--------|
| View all patients | ✅ | ❌ | ❌ |
| View patient details | ✅ (all) | ✅ (own) | ✅ (linked) |
| LLM training chat | ❌ | ✅ | ❌ |
| Upload recordings | ❌ | ✅ | ❌ |
| View voice assessments | ✅ (full) | ✅ (simplified) | ✅ (simplified) |
| View MRI results (raw) | ✅ | ❌ | ❌ |
| View diagnosis | ✅ | ✅ (own) | ✅ (linked) |
| Create diagnosis | ✅ | ❌ | ❌ |
| Update MCI stage | ✅ | ❌ | ❌ |
| View alerts/flags | ✅ | ❌ | ❌ |
| Manage family access | ✅ | ❌ | ❌ |
| Receive notifications | ✅ (critical) | ✅ (own) | ✅ (linked) |

---

## 8. Database Schema

### Complete Schema

```sql
-- 8.1 Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    google_id VARCHAR(255) UNIQUE,
    profile_picture VARCHAR(500),
    role VARCHAR(20) NOT NULL,          -- 'doctor', 'patient', 'family'
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- 8.2 Doctors
CREATE TABLE doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id),
    hospital VARCHAR(200),
    department VARCHAR(100),
    license_number VARCHAR(50),
    specialization VARCHAR(100)
);

-- 8.3 Patients
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id),
    date_of_birth DATE,
    phone VARCHAR(20),
    mci_stage VARCHAR(20),              -- 'normal', 'early_mci', 'late_mci', 'mild_dementia'
    diagnosis_date DATE,
    assigned_doctor_id UUID REFERENCES doctors(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_patients_doctor ON patients(assigned_doctor_id);

-- 8.4 Family Members
CREATE TABLE family_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    relationship VARCHAR(50),           -- 'spouse', 'child', 'sibling'
    can_view_recordings BOOLEAN DEFAULT false,
    can_view_transcripts BOOLEAN DEFAULT true,
    can_view_scores BOOLEAN DEFAULT true,
    approved_by UUID REFERENCES doctors(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_family_patient ON family_members(patient_id);
CREATE INDEX idx_family_user ON family_members(user_id);

-- 8.5 Training Sessions
CREATE TABLE training_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    exercise_type VARCHAR(50),          -- 'word_recall', 'story_retelling', 'daily_conversation'
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    conversation JSONB
);

CREATE INDEX idx_sessions_patient ON training_sessions(patient_id, started_at DESC);

-- 8.6 Recordings
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    session_id UUID REFERENCES training_sessions(id),
    audio_path VARCHAR(500) NOT NULL,
    duration_seconds FLOAT,
    file_size_bytes BIGINT,
    format VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT NOW(),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending'  -- 'pending', 'processing', 'completed', 'failed'
);

CREATE INDEX idx_recordings_patient ON recordings(patient_id, recorded_at DESC);
CREATE INDEX idx_recordings_status ON recordings(status) WHERE status != 'completed';

-- 8.7 Voice Assessments
CREATE TABLE voice_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID REFERENCES recordings(id),
    transcript TEXT,
    cognitive_score FLOAT,              -- 0-100
    mci_probability FLOAT,              -- 0-1
    flag VARCHAR(20) DEFAULT 'normal',  -- 'normal', 'warning', 'critical'
    flag_reasons JSONB,                 -- ["high_filler_rate", "long_pauses"]
    features JSONB,                     -- Detailed ML features
    model_version VARCHAR(50),
    assessed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_assessments_recording ON voice_assessments(recording_id);
CREATE INDEX idx_assessments_flag ON voice_assessments(flag) WHERE flag != 'normal';

-- 8.8 MRI Assessments
CREATE TABLE mri_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    scan_date TIMESTAMP,
    file_path VARCHAR(500),
    classification VARCHAR(20),         -- 'CN', 'EMCI', 'LMCI', 'AD'
    probabilities JSONB,                -- {"CN": 0.25, "EMCI": 0.21, "LMCI": 0.39, "AD": 0.15}
    confidence FLOAT,
    model_version VARCHAR(50),
    processed_at TIMESTAMP
);

CREATE INDEX idx_mri_patient ON mri_assessments(patient_id, scan_date DESC);

-- 8.9 Diagnoses
CREATE TABLE diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES doctors(id),
    diagnosis_date TIMESTAMP DEFAULT NOW(),
    mci_stage VARCHAR(20),
    confidence VARCHAR(20),             -- 'confirmed', 'suspected', 'uncertain'
    based_on_mri UUID REFERENCES mri_assessments(id),
    based_on_voice UUID REFERENCES voice_assessments(id),
    notes TEXT,
    follow_up_date DATE
);

CREATE INDEX idx_diagnoses_patient ON diagnoses(patient_id, diagnosis_date DESC);

-- 8.10 In-App Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    type VARCHAR(50) NOT NULL,          -- 'critical_flag', 'warning_flag', 'score_drop', 'new_diagnosis'
    title VARCHAR(200) NOT NULL,
    message TEXT,
    related_patient_id UUID REFERENCES patients(id),
    related_type VARCHAR(50),           -- 'assessment', 'diagnosis', 'patient'
    related_id UUID,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread 
ON notifications(user_id, is_read, created_at DESC) 
WHERE is_read = false;

-- 8.11 Model Versions
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500),
    accuracy FLOAT,
    notes TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 8.12 Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
```

---

## 9. API Endpoints

### 9.1 Authentication

```
GET    /api/auth/google              → Redirect to Google OAuth
GET    /api/auth/google/callback     → Google OAuth callback
GET    /api/auth/me                  → Get current user info
POST   /api/auth/logout              → Logout
```

### 9.2 Doctor Endpoints

```
GET    /api/doctor/patients                      → List all assigned patients
GET    /api/doctor/patients/{id}                 → Get patient details
PUT    /api/doctor/patients/{id}/stage           → Update MCI stage
POST   /api/doctor/patients                      → Add new patient
GET    /api/doctor/patients/{id}/recordings      → All recordings
GET    /api/doctor/patients/{id}/assessments     → All voice assessments
GET    /api/doctor/patients/{id}/mri             → All MRI results (full)
GET    /api/doctor/patients/{id}/progress        → Progress over time
POST   /api/doctor/diagnoses                     → Create diagnosis
GET    /api/doctor/patients/{id}/diagnoses       → Get diagnosis history
PUT    /api/doctor/diagnoses/{id}                → Update diagnosis
GET    /api/doctor/alerts                        → All flagged assessments
PUT    /api/doctor/alerts/{id}/resolve           → Mark as reviewed
GET    /api/doctor/patients/{id}/family          → List family members
POST   /api/doctor/patients/{id}/family          → Approve family access
DELETE /api/doctor/patients/{id}/family/{fid}    → Remove family access
```

### 9.3 Patient Endpoints

```
WS     /api/patient/chat                         → LLM training chat
GET    /api/patient/exercises                    → Available exercises
POST   /api/patient/recordings                   → Upload recording
GET    /api/patient/recordings                   → List own recordings
GET    /api/patient/recordings/{id}              → Get recording status
GET    /api/patient/progress                     → Own progress
GET    /api/patient/assessments                  → Own assessments
GET    /api/patient/diagnoses                    → Doctor's diagnoses
GET    /api/patient/profile                      → Get own profile
PUT    /api/patient/profile                      → Update profile
```

### 9.4 Family Endpoints

```
GET    /api/family/patient                       → Get linked patient info
GET    /api/family/patient/progress              → Patient's progress
GET    /api/family/patient/assessments           → Patient's assessments
GET    /api/family/patient/diagnoses             → Doctor's diagnoses
GET    /api/family/patient/sessions              → Training session history
GET    /api/family/profile                       → Get own profile
```

### 9.5 Notification Endpoints

```
GET    /api/notifications                        → Get notifications (paginated)
GET    /api/notifications/unread-count           → Get unread count (for badge 🔔)
PUT    /api/notifications/{id}/read              → Mark as read
PUT    /api/notifications/read-all               → Mark all as read
DELETE /api/notifications/{id}                   → Delete notification
```

---

## 10. Authentication (Google OAuth)

### Flow

```
1. User clicks "Login with Google"
2. Redirect to Google
3. User logs in on Google
4. Google redirects back with code
5. Backend exchanges code for user info
6. Backend creates JWT token
7. Frontend stores JWT
8. All API calls include: Authorization: Bearer <JWT>
```

### Implementation

```python
# src/auth/google.py
from authlib.integrations.starlette_client import OAuth
import os

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
```

---

## 11. OMV Storage Setup (Local SATA HAT)

### 11.1 Install Docker on OMV

SSH into the RPI/OMV host:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
exit
# SSH back in

# Verify
docker --version
docker compose version
```

### 11.2 Create Shared Folder in OMV

OMV Web UI → **Storage → Shared Folders** → Create:

| Name | Path |
|------|------|
| `mci-platform` | `/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final` |

### 11.3 Create Directory Structure

```bash
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final

mkdir -p code docker models postgres-data minio-data backups/postgres backups/minio
```

### 11.3.1 Important: PostgreSQL Data Must Stay Local (No NFS)

PostgreSQL ("PG") data should remain on the **local SSD filesystem** (ext4).  
With the SATA HAT, this is already local to the RPI. Do **not** place `postgres-data/` on NFS.  
Apps should connect to PostgreSQL via the Docker network when running on the same host.  
Reason: NFS can break PostgreSQL fsync/locking guarantees and lead to corruption under load.

Safe to export over NFS (optional, only if you share storage externally):
- `code/`
- `models/`
- `backups/` (optional)

Not safe to export over NFS:
- `postgres-data/`

NFS is not required for single-node deployments.

### 11.4 Optional: Enable NFS Share (only if external clients need it)

Skip this section for single-node SATA HAT setups.

OMV → **Services → NFS → Settings** → Enable

OMV → **Services → NFS → Shares** → Add:

| Shared Folder | Client | Options |
|---------------|--------|---------|
| mci-platform | 10.0.0.10 | `rw,sync,no_subtree_check,no_root_squash` |

### 11.5 Start Storage Containers (PostgreSQL + MinIO)

```bash
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker

# Create docker-compose.yml (recommended, see section 13)
# Create .env file (see section 27)

docker compose -f docker-compose.yml up -d
```

---

## 12. RPI 5 Setup

If OMV and the SATA HAT are on the same RPI, skip sections 12.2 and 12.4 (no NFS required).

### 12.1 Install Docker on RPI 5

```bash
# Update system
sudo apt update && sudo apt full-upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
exit
# SSH back in

# Verify
docker --version
docker compose version
```

### 12.2 Install NFS Client (Optional)

Only needed if you plan to mount this storage from another machine.

```bash
sudo apt install -y nfs-common
```

### 12.3 Set Static IP

```bash
sudo nmcli con mod "Wired connection 1" \
    ipv4.addresses 10.0.0.10/24 \
    ipv4.gateway 10.0.0.1 \
    ipv4.dns "8.8.8.8" \
    ipv4.method manual

sudo nmcli con up "Wired connection 1"
```

### 12.4 Local Storage (No NFS Mount)

```bash
# Verify local OMV path exists
ls /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final
```

### 12.5 Start RPI 5 Containers

```bash
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker

docker compose -f docker-compose.yml up -d
```

---

## 13. Docker Configuration

Recommended for single-node SATA HAT setups:

`docker compose -f docker-compose.yml up -d`

### 13.1 docker-compose.yml (Unified single-node)

This file combines the storage + compute services in one place.

### 13.2 docker-compose.nas.yml (Storage-only, optional)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: mci-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - ../postgres-data:/var/lib/postgresql/data
      - ../code/migrations:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: mci-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - ../minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
```

### 13.3 docker-compose.rpi.yml (Compute-only, optional)

Only needed if you want to split compute from storage.

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: mci-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ../code/nginx.conf:/etc/nginx/nginx.conf:ro
      - ../code/frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  api:
    build:
      context: ../code
      dockerfile: Dockerfile.api
    container_name: mci-api
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_USER}
      - MINIO_SECRET_KEY=${MINIO_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ../models:/models:ro
    expose:
      - "8000"
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build:
      context: ../code
      dockerfile: Dockerfile.worker
    container_name: mci-worker
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_USER}
      - MINIO_SECRET_KEY=${MINIO_PASSWORD}
      - OMP_NUM_THREADS=4
      - MKL_NUM_THREADS=4
      - OPENBLAS_NUM_THREADS=4
    volumes:
      - ../models:/models:ro
    depends_on:
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    container_name: mci-redis
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis-data:
```

### 13.3 Dockerfile.api (FastAPI + UV + Python 3.10)

```dockerfile
FROM python:3.10-slim-bookworm

# Install UV
RUN pip install uv

WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install dependencies with UV
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with UV
CMD ["uv", "run", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 13.4 Dockerfile.worker (Celery + ML + UV + Python 3.10)

```dockerfile
FROM python:3.10-slim-bookworm

# Install system dependencies for ML
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libopenblas-dev \
    libatlas-base-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install ALL dependencies including ML
RUN uv sync --frozen --all-extras

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# CPU Optimization environment variables
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4

# Run with UV
CMD ["uv", "run", "celery", "-A", "src.tasks", "worker", "--loglevel=info", "--concurrency=2"]
```

### 13.5 nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        client_max_body_size 500M;
        proxy_read_timeout 300s;

        # Health check
        location /health {
            return 200 'OK';
            add_header Content-Type text/plain;
        }

        # Vue.js static files
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # API proxy
        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_connect_timeout 60s;
            proxy_read_timeout 300s;
        }

        # WebSocket for LLM chat
        location /api/patient/chat {
            proxy_pass http://api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }
    }
}
```

---

## 14. UV Package Management

### 14.1 pyproject.toml

```toml
[project]
name = "mci-platform"
version = "0.1.0"
description = "MCI Cognitive Assessment Platform"
requires-python = ">=3.10"

dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.1",
    "celery>=5.3.6",
    "python-jose[cryptography]>=3.3.0",
    "authlib>=1.3.0",
    "httpx>=0.26.0",
    "python-multipart>=0.0.6",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
    "minio>=7.2.3",
    "openai>=1.12.0",
    "pyyaml>=6.0.1",
]

[project.optional-dependencies]
ml = [
    "torch>=2.1.0",
    "torchaudio>=2.1.0",
    "transformers>=4.37.0",
    "faster-whisper>=0.10.0",
    "kiwipiepy>=0.16.3",
    "librosa>=0.10.1",
    "soundfile>=0.12.1",
    "nibabel>=5.2.0",
    "scipy>=1.12.0",
    "scikit-image>=0.22.0",
    "catboost>=1.2.2",
    "pydicom>=2.4.4",
    "onnxruntime>=1.16.3",
]

dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
]
```

### 14.2 Initialize UV (First Time)

```bash
# On your development machine (not the RPI/OMV host)
cd /path/to/code

# Install UV
pip install uv

# Create lock file
uv lock

# This creates uv.lock - commit this to git
```

### 14.3 UV Commands Reference

```bash
# Install dependencies
uv sync

# Install with extras (ML)
uv sync --all-extras

# Add new package
uv add package-name

# Remove package
uv remove package-name

# Run command with UV environment
uv run python script.py
uv run pytest
uv run celery -A src.tasks worker
```

---

## 15. File Storage (MinIO)

### Bucket Structure

```
MinIO (http://10.0.0.10:9000)
├── voice-recordings/
│   └── {patient_id}/
│       └── {recording_id}.wav
├── mri-scans/
│   └── {patient_id}/
│       └── {study_id}/
│           └── *.dcm
├── processed/
│   ├── voice/
│   └── mri/
└── exports/
```

### Storage Service

```python
# src/storage.py
from minio import Minio
import os

class StorageService:
    def __init__(self):
        self.client = Minio(
            os.environ.get("MINIO_ENDPOINT"),
            access_key=os.environ.get("MINIO_ACCESS_KEY"),
            secret_key=os.environ.get("MINIO_SECRET_KEY"),
            secure=False
        )
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        buckets = ["voice-recordings", "mri-scans", "processed", "exports"]
        for bucket in buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
    
    def upload(self, file_path: str, bucket: str, object_name: str):
        self.client.fput_object(bucket, object_name, file_path)
    
    def download_temp(self, bucket: str, object_name: str) -> str:
        temp_path = f"/tmp/{object_name.replace('/', '_')}"
        self.client.fget_object(bucket, object_name, temp_path)
        return temp_path

storage = StorageService()
```

---

## 16. LLM Training System

### Prompt Configuration

```yaml
# config/prompts/exercises.yaml

word_recall:
  normal:
    system: |
      당신은 인지 훈련 도우미입니다.
      어려운 카테고리를 사용하여 빠른 속도로 진행합니다.
      20개 이상: 우수, 15-19개: 양호, 14개 이하: 추가 훈련 필요
    categories: ["과일", "나라", "ㄱ으로 시작하는 단어"]

  early_mci:
    system: |
      쉬운 카테고리로 천천히 진행합니다.
      힌트를 자연스럽게 제공합니다.
      10개 이상이면 칭찬합니다.
    categories: ["과일", "동물"]

  late_mci:
    system: |
      매우 친숙한 카테고리만 사용합니다.
      자주 격려하고 칭찬합니다.
      5개 이상이면 성공입니다.
    categories: ["과일", "가족"]

story_retelling:
  normal:
    system: |
      5-7문장의 이야기를 들려주고 세부 질문을 합니다.

daily_conversation:
  normal:
    system: |
      자연스러운 일상 대화를 나눕니다.
```

### Chat Service

```python
# src/llm/chat_service.py
from openai import OpenAI
import yaml

class PromptManager:
    def __init__(self):
        with open("config/prompts/exercises.yaml") as f:
            self.prompts = yaml.safe_load(f)
    
    def get_prompt(self, exercise_type: str, mci_stage: str) -> dict:
        return self.prompts.get(exercise_type, {}).get(mci_stage, {})

class ChatService:
    def __init__(self):
        self.client = OpenAI()
        self.prompt_manager = PromptManager()
    
    async def chat(self, exercise_type: str, mci_stage: str, message: str):
        prompt = self.prompt_manager.get_prompt(exercise_type, mci_stage)
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt.get("system", "")},
                {"role": "user", "content": message}
            ],
            stream=True
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

---

## 17. Voice ML Pipeline (CPU-Optimized)

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 VOICE ML PIPELINE (CPU-Optimized)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Audio File → Download from MinIO (local storage) → Process on RPI 5       │
│                                                                              │
│   STEP 1: Preprocessing              ⏱️ ~2-3 sec                            │
│   STEP 2: Whisper (small, INT8)      ⏱️ ~30-60 sec                          │
│   STEP 3a: wav2vec2 embeddings       ⏱️ ~20-40 sec                          │
│   STEP 3b: BERT embeddings           ⏱️ ~5-10 sec                           │
│   STEP 3c: Kiwi linguistic features  ⏱️ ~1-2 sec                            │
│   STEP 4: Feature fusion             ⏱️ instant                             │
│   STEP 5: Classification             ⏱️ <1 sec                              │
│   STEP 6: Flag & Notify              ⏱️ instant                             │
│                                                                              │
│   TOTAL: ~1-2 minutes                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Voice Pipeline Code

```python
# src/ml/voice_pipeline.py
import torch
import os
import numpy as np
from collections import Counter

# CPU Optimization
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
torch.set_num_threads(4)

class VoicePipelineCPU:
    """CPU-optimized voice pipeline for RPI 5"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        from faster_whisper import WhisperModel
        from transformers import Wav2Vec2Model, BertModel, BertTokenizer
        from kiwipiepy import Kiwi
        
        print("Loading ML models...")
        
        # Whisper small with INT8 quantization
        self.whisper = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8"
        )
        
        # Transformer models
        self.wav2vec = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")
        self.bert = BertModel.from_pretrained("klue/bert-base")
        self.bert_tokenizer = BertTokenizer.from_pretrained("klue/bert-base")
        
        self.wav2vec.eval()
        self.bert.eval()
        
        # Korean NLP
        self.kiwi = Kiwi()
        
        # Classifier
        self.classifier = torch.load("/models/voice_classifier.pt", map_location="cpu")
        self.classifier.eval()
        
        self._initialized = True
        print("ML models loaded!")
    
    def process(self, audio_path: str) -> dict:
        """Process audio and return assessment"""
        import librosa
        
        # Step 1: Preprocess
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        audio = audio / np.max(np.abs(audio))
        
        # Step 2: Transcribe
        segments, _ = self.whisper.transcribe(audio, language="ko")
        transcript = " ".join([s.text for s in segments])
        
        # Step 3: Extract features
        with torch.no_grad():
            audio_emb = self._get_audio_embedding(audio)
            text_emb = self._get_text_embedding(transcript)
        
        ling_features = self._get_linguistic_features(transcript)
        
        # Step 4: Combine
        combined = np.concatenate([
            audio_emb, text_emb, list(ling_features.values())
        ])
        
        # Step 5: Classify
        with torch.no_grad():
            tensor = torch.tensor(combined).float().unsqueeze(0)
            mci_prob = torch.sigmoid(self.classifier(tensor)).item()
        
        score = (1 - mci_prob) * 100
        
        # Step 6: Flag
        flag, reasons = self._calculate_flag(score, ling_features)
        
        return {
            "transcript": transcript,
            "cognitive_score": round(score, 2),
            "mci_probability": round(mci_prob, 4),
            "flag": flag,
            "flag_reasons": reasons,
            "features": ling_features
        }
    
    def _get_audio_embedding(self, audio: np.ndarray) -> np.ndarray:
        tensor = torch.tensor(audio).float().unsqueeze(0)
        outputs = self.wav2vec(tensor)
        return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    
    def _get_text_embedding(self, text: str) -> np.ndarray:
        inputs = self.bert_tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512, padding=True
        )
        outputs = self.bert(**inputs)
        return outputs.last_hidden_state[:, 0, :].squeeze().numpy()
    
    def _get_linguistic_features(self, text: str) -> dict:
        tokens = self.kiwi.tokenize(text)
        if not tokens:
            return {f"feature_{i}": 0 for i in range(21)}
        
        pos_counts = Counter([t.tag for t in tokens])
        total = len(tokens)
        
        fillers = sum(1 for t in tokens if t.form in ["음", "어", "그", "저", "뭐"])
        deictics = sum(1 for t in tokens if t.form in ["그거", "저거", "이거"])
        nouns = pos_counts.get("NNG", 0) + pos_counts.get("NNP", 0)
        verbs = pos_counts.get("VV", 0)
        
        features = {
            "filler_rate": fillers / total,
            "deictic_rate": deictics / total,
            "noun_count": nouns,
            "verb_count": verbs,
            "noun_verb_ratio": nouns / max(verbs, 1),
            "total_tokens": total,
            "unique_tokens": len(set(t.form for t in tokens)),
            "lexical_diversity": len(set(t.form for t in tokens)) / total,
        }
        
        # Pad to 21 features
        for i in range(len(features), 21):
            features[f"feature_{i}"] = 0
        
        return features
    
    def _calculate_flag(self, score: float, features: dict) -> tuple:
        flag = "normal"
        reasons = []
        
        if score < 40:
            flag = "critical"
            reasons.append("very_low_score")
        elif score < 60:
            flag = "warning"
            reasons.append("low_score")
        
        if features.get("filler_rate", 0) > 0.15:
            if flag != "critical":
                flag = "warning"
            reasons.append("high_filler_rate")
        
        return flag, reasons


def get_voice_pipeline():
    return VoicePipelineCPU()
```

---

## 18. MRI ML Pipeline (CPU-Optimized)

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  MRI ML PIPELINE (CPU-Optimized)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PREPROCESSING:                                                            │
│   1. DICOM → NIfTI                    ⏱️ ~10 sec                            │
│   2. Denoising                        ⏱️ ~20 sec                            │
│   3. Skull Stripping                  ⏱️ ~30 sec                            │
│   4. Centering                        ⏱️ ~5 sec                             │
│   5. Robust-Score Normalization       ⏱️ ~5 sec                             │
│   6. Resize to 128×128×128            ⏱️ ~5 sec                             │
│                                                                              │
│   CLASSIFICATION:                                                           │
│   Model 1: CN vs Impaired (3D CNN)    ⏱️ ~1-2 min                           │
│   Model 2: AD vs MCI (3D CNN)         ⏱️ ~1-2 min                           │
│   Model 3: EMCI vs LMCI (CatBoost)    ⏱️ ~1 sec                             │
│                                                                              │
│   TOTAL: ~3-7 minutes                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MRI Pipeline Code

```python
# src/ml/mri_pipeline.py
import torch
import nibabel as nib
import numpy as np
from scipy.ndimage import zoom, center_of_mass, shift
from skimage.restoration import denoise_nl_means
from catboost import CatBoostClassifier
import os

os.environ["OMP_NUM_THREADS"] = "4"
torch.set_num_threads(4)


class MRIPreprocessor:
    """MRI preprocessing pipeline"""
    
    def preprocess(self, dicom_path: str) -> np.ndarray:
        """
        1. DICOM → NIfTI
        2. Denoise
        3. Skull strip
        4. Center
        5. Robust-score normalize
        6. Resize to 128×128×128
        """
        nifti = self._convert_dicom(dicom_path)
        denoised = self._denoise(nifti)
        brain = self._skull_strip(denoised)
        centered = self._center(brain)
        normalized = self._normalize_robust(centered)
        resized = self._resize(normalized)
        return resized
    
    def _convert_dicom(self, dicom_path: str):
        import pydicom
        from glob import glob
        
        dicom_files = sorted(glob(f"{dicom_path}/*.dcm"))
        slices = [pydicom.dcmread(f) for f in dicom_files]
        slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
        pixel_array = np.stack([s.pixel_array for s in slices])
        return nib.Nifti1Image(pixel_array.astype(np.float32), np.eye(4))
    
    def _denoise(self, img):
        data = img.get_fdata()
        denoised = denoise_nl_means(data, h=1.0, patch_size=3, patch_distance=4, fast_mode=True)
        return nib.Nifti1Image(denoised, img.affine)
    
    def _skull_strip(self, img):
        data = img.get_fdata()
        from scipy.ndimage import binary_fill_holes, binary_erosion, binary_dilation
        
        threshold = np.percentile(data[data > 0], 20)
        mask = data > threshold
        mask = binary_fill_holes(mask)
        mask = binary_erosion(mask, iterations=1)
        mask = binary_dilation(mask, iterations=1)
        
        return nib.Nifti1Image(data * mask, img.affine)
    
    def _center(self, img):
        data = img.get_fdata()
        com = center_of_mass(data > 0)
        target = np.array(data.shape) / 2
        centered = shift(data, target - np.array(com), mode='constant', cval=0)
        return nib.Nifti1Image(centered, img.affine)
    
    def _normalize_robust(self, img):
        """Robust-score: (x - median) / IQR"""
        data = img.get_fdata()
        brain_voxels = data[data > 0]
        median = np.median(brain_voxels)
        q75, q25 = np.percentile(brain_voxels, [75, 25])
        iqr = max(q75 - q25, 1)
        return nib.Nifti1Image((data - median) / iqr, img.affine)
    
    def _resize(self, img, target=(128, 128, 128)):
        data = img.get_fdata()
        factors = [t / s for t, s in zip(target, data.shape)]
        return zoom(data, factors, order=1)


class MRIPipelineCPU:
    """CPU-optimized MRI classification pipeline"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        print("Loading MRI models...")
        
        self.preprocessor = MRIPreprocessor()
        self.model1 = torch.load("/models/mri_model1.pt", map_location="cpu")
        self.model2 = torch.load("/models/mri_model2.pt", map_location="cpu")
        self.model3 = CatBoostClassifier()
        self.model3.load_model("/models/catboost_subtype.cbm")
        
        self.model1.eval()
        self.model2.eval()
        
        self._initialized = True
        print("MRI models loaded!")
    
    def process(self, dicom_path: str, clinical_data: dict = None) -> dict:
        clinical_data = clinical_data or {}
        
        # Preprocess
        processed = self.preprocessor.preprocess(dicom_path)
        tensor = torch.tensor(processed).float().unsqueeze(0).unsqueeze(0)
        
        with torch.no_grad():
            # Model 1: CN vs Impaired
            p1 = torch.sigmoid(self.model1(tensor)).item()
            if p1 < 0.5:
                return self._build_result(p1, 0, 0)
            
            # Model 2: AD vs MCI
            p2 = torch.sigmoid(self.model2(tensor)).item()
            if p2 < 0.5:
                return self._build_result(p1, p2, 0)
        
        # Model 3: EMCI vs LMCI
        features = {"mri_p1": p1, "mri_p2": p2, **clinical_data}
        p3 = self.model3.predict_proba([list(features.values())])[0][1]
        
        return self._build_result(p1, p2, p3)
    
    def _build_result(self, p1: float, p2: float, p3: float) -> dict:
        probs = {
            "CN": round(1 - p1, 4),
            "AD": round(p1 * (1 - p2), 4),
            "EMCI": round(p1 * p2 * (1 - p3), 4),
            "LMCI": round(p1 * p2 * p3, 4)
        }
        classification = max(probs, key=probs.get)
        return {
            "classification": classification,
            "probabilities": probs,
            "confidence": probs[classification]
        }


def get_mri_pipeline():
    return MRIPipelineCPU()
```

---

## 19. Celery Background Tasks

```python
# src/tasks.py
from celery import Celery
import os

os.environ["OMP_NUM_THREADS"] = "4"

celery_app = Celery(
    'tasks',
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)


@celery_app.task(bind=True, max_retries=2)
def process_voice_recording(self, recording_id: str):
    """Process voice recording in background"""
    try:
        from src.ml.voice_pipeline import get_voice_pipeline
        from src.storage import storage
        from src.database import db
        from src.notifications.service import notification_service
        
        # Update status
        db.execute("UPDATE recordings SET status = 'processing' WHERE id = $1", recording_id)
        
        # Download from MinIO
        audio_path = storage.download_temp("voice-recordings", f"{recording_id}.wav")
        
        # Process
        pipeline = get_voice_pipeline()
        result = pipeline.process(audio_path)
        
        # Save
        db.execute("""
            INSERT INTO voice_assessments 
            (recording_id, transcript, cognitive_score, mci_probability, flag, flag_reasons, features)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, recording_id, result["transcript"], result["cognitive_score"],
             result["mci_probability"], result["flag"], result["flag_reasons"], result["features"])
        
        db.execute("UPDATE recordings SET status = 'completed' WHERE id = $1", recording_id)
        
        # Notify if needed
        if result["flag"] in ["critical", "warning"]:
            notification_service.notify_doctor_flag(recording_id, result["flag"])
        
        # Cleanup
        os.remove(audio_path)
        
        return {"status": "completed", "score": result["cognitive_score"]}
    
    except Exception as e:
        db.execute("UPDATE recordings SET status = 'failed' WHERE id = $1", recording_id)
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=2)
def process_mri_scan(self, patient_id: str, dicom_path: str, clinical_data: dict = None):
    """Process MRI scan in background"""
    try:
        from src.ml.mri_pipeline import get_mri_pipeline
        from src.database import db
        
        pipeline = get_mri_pipeline()
        result = pipeline.process(dicom_path, clinical_data)
        
        db.execute("""
            INSERT INTO mri_assessments 
            (patient_id, classification, probabilities, confidence, processed_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, patient_id, result["classification"], result["probabilities"], result["confidence"])
        
        return result
    
    except Exception as e:
        raise self.retry(exc=e, countdown=120)
```

---

## 20. Model Versioning

```yaml
# config/models.yaml

voice:
  classifier:
    version: "v1.0.0"
    path: "/models/voice_classifier.pt"
  whisper:
    model: "small"
    compute_type: "int8"

mri:
  model1:
    version: "v1.0.0"
    path: "/models/mri_model1.pt"
  model2:
    version: "v1.0.0"
    path: "/models/mri_model2.pt"
  catboost:
    version: "v1.0.0"
    path: "/models/catboost_subtype.cbm"
```

---

## 21. In-App Notification System

### Notification Types

```python
# src/notifications/types.py
from enum import Enum

class NotificationType(str, Enum):
    CRITICAL_FLAG = "critical_flag"
    WARNING_FLAG = "warning_flag"
    SCORE_DROP = "score_drop"
    NEW_DIAGNOSIS = "new_diagnosis"
    FAMILY_APPROVED = "family_approved"
    NEW_ASSESSMENT = "new_assessment"
```

### Notification Service

```python
# src/notifications/service.py
from datetime import datetime
from src.database import db
from src.notifications.types import NotificationType

class NotificationService:
    async def create(self, user_id: str, type: str, title: str, message: str,
                     related_patient_id: str = None, related_type: str = None, related_id: str = None):
        await db.execute("""
            INSERT INTO notifications 
            (user_id, type, title, message, related_patient_id, related_type, related_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, user_id, type, title, message, related_patient_id, related_type, related_id)
    
    async def get_unread_count(self, user_id: str) -> int:
        result = await db.fetchone(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = $1 AND is_read = false",
            user_id
        )
        return result["count"]
    
    async def mark_as_read(self, notification_id: str, user_id: str):
        await db.execute("""
            UPDATE notifications SET is_read = true, read_at = $1 
            WHERE id = $2 AND user_id = $3
        """, datetime.now(), notification_id, user_id)
    
    async def notify_doctor_critical(self, doctor_id: str, patient_name: str, assessment_id: str):
        await self.create(
            user_id=doctor_id,
            type=NotificationType.CRITICAL_FLAG,
            title="🚨 위험 알림",
            message=f"{patient_name} 환자의 평가 결과가 위험 수준입니다.",
            related_type="assessment",
            related_id=assessment_id
        )

notification_service = NotificationService()
```

---

## 22. Logging & Monitoring

### View Logs

```bash
# On RPI 5
docker logs -f mci-api
docker logs -f mci-worker
docker logs -f mci-redis

# On RPI 5 (storage services)
docker logs -f mci-postgres
docker logs -f mci-minio
```

### Monitor Health

```bash
# RPI 5 temperature
vcgencmd measure_temp

# Container status
docker ps

# Resource usage
docker stats

# Network to router
ping 10.0.0.1
```

---

## 23. Backup Strategy

### Automated Backup Script

```bash
#!/bin/bash
# code/scripts/backup.sh

DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR="/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/backups"

# PostgreSQL backup
echo "Backing up PostgreSQL..."
docker exec mci-postgres pg_dump -U mci_user cognitive | gzip > "$BACKUP_DIR/postgres/backup_$DATE.sql.gz"

# Keep last 30 days
find $BACKUP_DIR/postgres -name "*.sql.gz" -mtime +30 -delete

echo "Backup complete!"
```

### Cron Job (on RPI 5)

```bash
crontab -e

# Daily backup at 2 AM
0 2 * * * /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/code/scripts/backup.sh >> /var/log/mci-backup.log 2>&1
```

---

## 24. Testing Guide

```bash
# Run tests in Docker
docker exec mci-api uv run pytest

# With coverage
docker exec mci-api uv run pytest --cov=src tests/

# Specific test
docker exec mci-api uv run pytest tests/test_notifications.py -v
```

---

## 25. Deployment

### First Time Setup

```bash
# Start storage + compute services on RPI 5
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker
docker compose -f docker-compose.yml up -d
```

### Update Deployment

```bash
# Pull new code
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/code
git pull origin main

# Rebuild and restart
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d
```

### Stop Services

```bash
# RPI 5 (all services)
docker compose -f docker-compose.yml down
```

### Full Cleanup (removes everything)

```bash
# Removes containers, images, volumes
docker compose -f docker-compose.yml down -v --rmi all
```

---

## 26. Mobile App Considerations

PWA (Progressive Web App) is recommended - works great with this setup.

```javascript
// frontend/vite.config.js
import { VitePWA } from 'vite-plugin-pwa'

export default {
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'MCI Assessment Platform',
        short_name: 'MCI',
        theme_color: '#4A90A4'
      }
    })
  ]
}
```

---

## 27. Environment Variables

### docker/.env

```bash
# Database
POSTGRES_USER=mci_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=cognitive

# MinIO
MINIO_USER=minioadmin
MINIO_PASSWORD=your_secure_password

# Network
# No NAS_IP required for single-node SATA HAT setups

# OpenAI
OPENAI_API_KEY=sk-...

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# JWT
JWT_SECRET=your-very-secure-random-string
```

---

## 28. Development Phases

| Phase | Scope | Time |
|-------|-------|------|
| Phase 1 | Auth + Dashboards | 2-3 weeks |
| Phase 2 | LLM Training + Voice Recording | 2-3 weeks |
| Phase 3 | Voice ML Pipeline | 3-4 weeks |
| Phase 4 | MRI Pipeline | 3-4 weeks |
| Phase 5 | Notifications + Monitoring | 1-2 weeks |
| Phase 6 | Mobile (PWA) | 2-3 weeks |

---

## 29. Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs mci-api

# Check local storage path
ls /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final
```

### Database Connection Failed

```bash
# Check PostgreSQL (local)
docker logs mci-postgres

# Test connection from RPI 5
docker exec mci-api uv run python -c "
import asyncpg
import asyncio
asyncio.run(asyncpg.connect('postgresql://mci_user:password@postgres:5432/cognitive'))
print('Connected!')
"
```

### Slow Processing

```bash
# Check RPI 5 temperature (throttling?)
vcgencmd measure_temp

# Check CPU frequency
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# Disk usage
df -h
```

### Out of Memory

```bash
# Check memory
free -h
docker stats

# Reduce worker concurrency in docker-compose.yml
# Change: concurrency=2 → concurrency=1
```

---

## Quick Start Commands

```bash
# Start everything (single-node)
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker && docker compose -f docker-compose.yml up -d

# Check status
docker ps

# View logs
docker logs -f mci-worker

# Stop everything
docker compose -f docker-compose.yml down

# Rebuild after code changes
docker compose -f docker-compose.yml build && docker compose -f docker-compose.yml up -d
```

---

## Summary

| Component | Location | Technology |
|-----------|----------|------------|
| Code | RPI 5 (OMV local) | Git repo |
| PostgreSQL | RPI 5 (OMV local) | Docker |
| MinIO | RPI 5 (OMV local) | Docker |
| ML Models | RPI 5 (OMV local) | .pt, .cbm files |
| FastAPI | RPI 5 | Docker + UV + Python 3.10 |
| Celery | RPI 5 | Docker + UV + Python 3.10 |
| Redis | RPI 5 | Docker |
| Nginx | RPI 5 | Docker |

**Processing Times:**
- Voice: ~1-2 minutes ✅
- MRI: ~3-7 minutes ✅

**No Python installed on host systems - everything runs in Docker!** 🐳
