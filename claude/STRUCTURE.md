# MCI Platform - Optimized Directory Structure

**Last Updated:** 2026-02-07

---

## 📁 Complete Directory Layout

```
/srv/.../final/                          ← Project Root
│
├── 📚 Documentation & Tracking
│   └── ~/claude/                        ← Your documentation folder
│       ├── PROJECT_SUMMARY.md          (31KB) - Full project overview
│       ├── CHECKLIST.md                (18KB) - Detailed task checklist
│       ├── PROGRESS_UPDATE.md          (7KB)  - Session progress
│       ├── FILES_CREATED.md            (7KB)  - What was created
│       └── STRUCTURE.md                (this file) - Directory layout
│
├── 💻 Source Code
│   └── src/
│       └── claude/                      ← Main application code
│           ├── __init__.py
│           └── app/
│               ├── __init__.py
│               ├── main.py              FastAPI app entry point
│               ├── config.py            Pydantic settings
│               ├── db.py                AsyncPG database pool
│               ├── storage.py           MinIO file storage
│               │
│               ├── schemas/             Pydantic models (10 files)
│               │   ├── user.py
│               │   ├── doctor.py
│               │   ├── patient.py
│               │   ├── family.py
│               │   ├── recording.py
│               │   ├── assessment.py
│               │   ├── diagnosis.py
│               │   ├── training.py
│               │   ├── auth.py
│               │   └── notifications.py
│               │
│               └── routers/             API endpoints (6 files)
│                   ├── health.py        ✅ 4 endpoints
│                   ├── doctor.py        ✅ 16 endpoints
│                   ├── notifications.py ✅ 6 endpoints
│                   ├── patient.py       ⏳ 10 stubs
│                   ├── family.py        ⏳ 6 stubs
│                   └── auth.py          ⏳ 4 stubs
│
├── 🗄️ Database
│   ├── migrations/
│   │   ├── 000_placeholder.sql
│   │   └── 001_init.sql                 ✅ All 12 tables
│   └── postgres-data/                   (auto-created by Docker)
│
├── 📦 File Storage
│   ├── minio-data/                      (MinIO object storage)
│   │   ├── .minio.sys/                  (MinIO system files)
│   │   ├── voice-recordings/            (future: patient audio)
│   │   ├── mri-scans/                   (future: DICOM files)
│   │   ├── processed/                   (future: ML outputs)
│   │   └── exports/                     (future: data exports)
│   │
│   └── models/                          (ML model files - empty for now)
│       ├── voice_classifier.pt          (TODO)
│       ├── mri_model1.pt                (TODO)
│       ├── mri_model2.pt                (TODO)
│       └── catboost_subtype.cbm         (TODO)
│
├── 🎨 Frontend
│   └── frontend/
│       └── dist/                        (placeholder Vue.js build)
│           └── index.html
│
├── 🐳 Docker Configuration
│   ├── docker/
│   │   ├── docker-compose.yml           ✅ 6 services configured
│   │   ├── .env                         ✅ Environment variables
│   │   └── Dockerfile                   (optional extra)
│   │
│   ├── Dockerfile.api                   ✅ FastAPI container
│   ├── Dockerfile.worker                ⏳ Celery container (needs update)
│   └── nginx.conf                       ✅ Frontend + API proxy
│
├── 🔧 Configuration
│   ├── pyproject.toml                   ✅ UV package config
│   ├── uv.lock                          ✅ Locked dependencies
│   ├── .env.example                     (TODO)
│   ├── .gitignore                       ✅
│   └── .python-version                  ✅ (3.10)
│
├── 📝 Project Documentation
│   ├── README.md                        ✅ Basic setup instructions
│   └── MCI_PLATFORM_ARCHITECTURE_*.md   ✅ Architecture docs
│
└── 🧪 Testing (TODO)
    └── tests/
        ├── conftest.py
        ├── test_auth.py
        ├── test_doctor.py
        └── test_notifications.py
```

---

## 🗂️ File Count by Type

| Category | Files | Status |
|----------|-------|--------|
| **Python Source** | 22 files | ✅ Core done |
| **Pydantic Schemas** | 10 files | ✅ Complete |
| **API Routers** | 6 files | 🟡 3/6 done |
| **SQL Migrations** | 1 file | ✅ Complete |
| **Docker Files** | 4 files | ✅ Complete |
| **Documentation** | 6 files | ✅ Complete |
| **Frontend** | 1 file | ⏳ Placeholder |
| **Tests** | 0 files | ❌ Not started |

---

## 📊 Size Breakdown

```
Total Project Size: ~250MB
├── postgres-data/     ~150MB (database)
├── minio-data/        ~80MB  (MinIO system)
├── .venv/             ~15MB  (Python packages)
├── src/claude/        ~120KB (source code)
├── ~/claude/          ~62KB  (documentation)
└── other              ~5MB   (config, git, etc.)
```

---

## 🎯 Key Directories Explained

### 1. `~/claude/` - Your Command Center
**Purpose:** Documentation and progress tracking
**Contains:** All .md files for reference
**Usage:** Read these to understand project status

### 2. `src/claude/app/` - Application Core
**Purpose:** FastAPI application code
**Contains:** All business logic, API endpoints, database models
**Usage:** This is where development happens

### 3. `docker/` - Container Configuration
**Purpose:** Docker Compose setup
**Contains:** Service definitions, environment variables
**Usage:** `docker compose up` to start services

### 4. `migrations/` - Database Schema
**Purpose:** PostgreSQL table definitions
**Contains:** SQL migration files
**Usage:** Auto-applied on container start

### 5. `models/` - ML Models
**Purpose:** Pre-trained AI models
**Contains:** PyTorch and CatBoost model files (empty for now)
**Usage:** Loaded by worker container for inference

---

## ✅ Optimizations Applied

1. ✅ Removed duplicate `src/gpt/` directory (saved 136KB)
2. ✅ Removed typo directory `src/cluade/`
3. ✅ Consolidated all source in `src/claude/`
4. ✅ All documentation in `~/claude/`
5. ✅ Updated Dockerfile.api to use correct path
6. ✅ Clean separation: code vs config vs data

---

## 🚀 Quick Navigation

### To view documentation:
```bash
cd ~/claude
ls -la
cat PROJECT_SUMMARY.md
```

### To work on code:
```bash
cd /srv/.../final/src/claude/app
ls -la routers/
```

### To start Docker:
```bash
cd /srv/.../final/docker
docker compose up -d
```

### To check database:
```bash
cd /srv/.../final/migrations
cat 001_init.sql
```

---

## 📝 File Naming Conventions

- **Schemas:** Singular nouns (user.py, patient.py)
- **Routers:** Plural nouns (doctors.py) or singular (health.py)
- **Services:** Descriptive (storage.py, db.py)
- **Migrations:** Numbered (001_init.sql, 002_add_column.sql)

---

## 🔄 Update History

- **2026-02-07:** Initial structure created
- **2026-02-07:** Removed src/gpt/ duplicate
- **2026-02-07:** Cleaned up typo directories
- **2026-02-07:** Created STRUCTURE.md

---

**End of Structure Document**
