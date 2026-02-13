-- ============================================================================
-- MCI PLATFORM - READABLE SCHEMA BLUEPRINT (DRAFT)
-- ============================================================================
-- Purpose:
-- - Human-readable SQL to understand the full data model.
-- - Includes MRI/voice model outputs, clinical data, and MinIO metadata.
--
-- Important:
-- - This is a blueprint/reference file, not an executable migration plan.
-- - Do NOT run this directly on production.
-- ============================================================================


-- ============================================================================
-- 1) IDENTITY + ACCESS
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    google_id VARCHAR(255) UNIQUE,
    profile_picture VARCHAR(500),
    role VARCHAR(20) NOT NULL,              -- doctor | patient | family
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE doctors (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    hospital VARCHAR(200),
    department VARCHAR(100),
    license_number VARCHAR(50),
    specialization VARCHAR(100)
);

CREATE TABLE patients (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    assigned_doctor_id UUID REFERENC5ES doctors(id),

    -- platform diagnosis state (doctor decides)
    mci_stage VARCHAR(20),                  -- CN | sMCI | pMCI | AD | unknown
    diagnosis_date DATE,

    -- demographics + ADNI linkage
    date_of_birth DATE,
    phone VARCHAR(20),
    rid INTEGER,
    subject_id VARCHAR(20),
    gender SMALLINT,                        -- 1 male, 2 female
    ptdobyy DATE,
    apoe4 SMALLINT,                         -- 0,1,2

    -- dashboard cache fields
    enrollment_date DATE,
    hospital VARCHAR(200),
    risk_level VARCHAR(10),                 -- low | mid | high
    last_session_at TIMESTAMP,
    participation_rate FLOAT,
    emergency_contact VARCHAR(100),
    emergency_phone VARCHAR(20),

    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE TABLE family_members (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    relationship VARCHAR(50),
    can_view_recordings BOOLEAN NOT NULL DEFAULT false,
    can_view_transcripts BOOLEAN NOT NULL DEFAULT true,
    can_view_scores BOOLEAN NOT NULL DEFAULT true,
    approved_by UUID REFERENCES doctors(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE user_settings (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    notification_email BOOLEAN NOT NULL DEFAULT true,
    notification_push BOOLEAN NOT NULL DEFAULT true,
    notification_critical_only BOOLEAN NOT NULL DEFAULT false,
    language VARCHAR(10) NOT NULL DEFAULT 'ko',
    display_preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    related_patient_id UUID REFERENCES patients(id),
    related_type VARCHAR(50),
    related_id UUID,
    is_read BOOLEAN NOT NULL DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL
);


-- ============================================================================
-- 2) TRAINING + VOICE PIPELINE
-- ============================================================================

CREATE TABLE training_sessions (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    exercise_type VARCHAR(50),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    mood VARCHAR(20),
    score FLOAT,
    summary TEXT,
    conversation JSONB
);

CREATE TABLE recordings (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    session_id UUID REFERENCES training_sessions(id),

    -- canonical storage columns
    audio_path VARCHAR(500) NOT NULL,
    duration_seconds FLOAT,
    file_size_bytes BIGINT,
    format VARCHAR(20),
    recorded_at TIMESTAMP,
    uploaded_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,           -- pending | processing | completed | failed

    -- compatibility fields currently used by app code
    file_path VARCHAR(500),
    file_size BIGINT,
    recording_date TIMESTAMP,
    description TEXT,
    created_at TIMESTAMP,
    transcription TEXT,
    exercise_type VARCHAR(50),

    -- optional link to MinIO object catalog
    storage_object_id UUID
);

CREATE TABLE voice_assessments (
    id UUID PRIMARY KEY,
    recording_id UUID NOT NULL REFERENCES recordings(id),

    transcript TEXT,
    cognitive_score FLOAT,                 -- 0-100
    mci_probability FLOAT,                 -- 0-1
    flag VARCHAR(20) NOT NULL,             -- normal | warning | critical
    flag_reasons JSONB,

    -- model outputs and explainability
    features JSONB,                        -- high-dimensional ML features
    acoustic_summary JSONB,                -- pitch, energy, pauses, speech_rate
    predicted_stage VARCHAR(20),           -- CN | sMCI | pMCI | AD (derived/helper)
    confidence_score FLOAT,
    model_version VARCHAR(50),

    assessed_at TIMESTAMP,
    created_at TIMESTAMP
);


-- ============================================================================
-- 3) MRI PIPELINE + DIAGNOSIS
-- ============================================================================

CREATE TABLE mri_assessments (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),

    -- raw source linkage
    image_id INTEGER,                      -- ADNI image id
    file_path VARCHAR(500),                -- primary path
    image_paths JSONB,                     -- processed/intermediate paths

    -- model outputs
    classification VARCHAR(20),            -- CN | EMCI | LMCI | AD
    probabilities JSONB,                   -- class probabilities
    confidence FLOAT,
    predicted_stage VARCHAR(20),           -- CN | sMCI | pMCI | AD
    confidence_score FLOAT,

    -- explainability and processing state
    preprocessing_status VARCHAR(20),      -- pending | processing | completed | failed
    region_contributions JSONB,
    volumetric_data JSONB,
    ai_analysis JSONB,
    doctor_diagnosis JSONB,
    brain_volume FLOAT,
    hippocampal_volume FLOAT,
    ventricle_volume FLOAT,

    model_version VARCHAR(50),
    scan_date TIMESTAMP,
    processed_at TIMESTAMP,
    created_at TIMESTAMP,
    storage_object_id UUID
);

CREATE TABLE diagnoses (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    doctor_id UUID NOT NULL REFERENCES doctors(id),
    diagnosis_date TIMESTAMP NOT NULL,
    mci_stage VARCHAR(20) NOT NULL,        -- CN | sMCI | pMCI | AD
    confidence VARCHAR(20),                -- confirmed | suspected | uncertain
    based_on_mri UUID REFERENCES mri_assessments(id),
    based_on_voice UUID REFERENCES voice_assessments(id),
    notes TEXT,
    follow_up_date DATE
);


-- ============================================================================
-- 4) CLINICAL / ADNI TABLES
-- ============================================================================

CREATE TABLE visits (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    exam_date DATE NOT NULL,
    viscode2 VARCHAR(10),                  -- sc, bl, m06, m12, ...
    origprot VARCHAR(10),                  -- ADNI protocol
    colprot VARCHAR(10),
    image_id INTEGER,
    mri_assessment_id UUID REFERENCES mri_assessments(id),
    notes TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE clinical_tests (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    visit_id UUID REFERENCES visits(id),
    exam_date DATE NOT NULL,
    viscode2 VARCHAR(10),

    mmse INTEGER,
    moca FLOAT,
    adas_cog13 FLOAT,
    cdr_global FLOAT,
    cdr_memory FLOAT,
    cdr_sb FLOAT,
    faq FLOAT,
    gds FLOAT,
    cci FLOAT,
    nxaudito SMALLINT,

    notes TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE neuropsych_tests (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    visit_id UUID REFERENCES visits(id),
    exam_date DATE NOT NULL,
    viscode2 VARCHAR(10),

    -- RAVLT
    avtot1 FLOAT,
    avtot2 FLOAT,
    avtot3 FLOAT,
    avtot4 FLOAT,
    avtot5 FLOAT,
    avtot6 FLOAT,
    avtotb FLOAT,
    avdel30min FLOAT,
    avdeltot FLOAT,
    averr1 FLOAT,
    averr2 FLOAT,
    ravlt_immediate FLOAT,
    ravlt_learning FLOAT,
    ravlt_forgetting FLOAT,
    ravlt_pct_forgetting FLOAT,

    -- Trail Making
    traascor FLOAT,
    trabscor FLOAT,

    notes TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE biomarkers (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    visit_id UUID REFERENCES visits(id),
    collected_date DATE NOT NULL,
    sample_type VARCHAR(20) NOT NULL,      -- csf | blood

    abeta42 FLOAT,
    abeta40 FLOAT,
    ptau FLOAT,
    tau FLOAT,
    ab42_ab40 FLOAT,
    ptau_ab42 FLOAT,
    ttau_ab42 FLOAT,

    notes TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE caregiver_observations (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    family_member_id UUID NOT NULL REFERENCES family_members(id),
    observation_date DATE NOT NULL,
    category VARCHAR(50),                  -- memory/behavior/mood/daily_activity/sleep/medication
    content TEXT NOT NULL,
    severity VARCHAR(10) NOT NULL,         -- normal | concern | urgent
    created_at TIMESTAMP NOT NULL
);


-- ============================================================================
-- 5) STORAGE / MODEL / INGEST
-- ============================================================================

CREATE TABLE model_versions (
    id UUID PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500),
    accuracy FLOAT,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE storage_objects (
    id UUID PRIMARY KEY,
    bucket VARCHAR(63) NOT NULL,           -- MinIO bucket
    object_key TEXT NOT NULL,              -- path inside bucket
    object_version VARCHAR(255),
    etag VARCHAR(128),
    size_bytes BIGINT,
    content_type VARCHAR(255),
    checksum_sha256 VARCHAR(64),
    source_type VARCHAR(30),               -- voice_recording/mri_raw/mri_processed/model/export/other
    source_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}',
    uploaded_by_user_id UUID REFERENCES users(id),
    uploaded_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
);

CREATE TABLE mri_files (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(id),
    visit_id UUID REFERENCES visits(id),
    image_id INTEGER,
    bucket VARCHAR(63) NOT NULL,
    raw_object_key TEXT NOT NULL,          -- raw MRI object key
    raw_format VARCHAR(20),                -- dicom, nifti, nii.gz
    upload_status VARCHAR(20) NOT NULL,    -- uploaded | failed | deleted
    preprocessing_status VARCHAR(20) NOT NULL, -- pending | processing | completed | failed
    processed_object_keys JSONB NOT NULL DEFAULT '[]',
    checksum_sha256 VARCHAR(64),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE data_ingest_runs (
    id UUID PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,     -- adni_baseline_csv, etc.
    source_file VARCHAR(500),
    status VARCHAR(20) NOT NULL,           -- pending | running | completed | failed
    rows_total INTEGER NOT NULL DEFAULT 0,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    rows_updated INTEGER NOT NULL DEFAULT 0,
    rows_failed INTEGER NOT NULL DEFAULT 0,
    error_log TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP
);


-- ============================================================================
-- 6) RELATIONSHIPS (ERD REFERENCE)
-- ============================================================================
-- Cardinality guide:
-- - "1:1" means one row maps to at most one row in the target table.
-- - "1:N" means one row maps to multiple rows in the target table.
--
-- Identity and roles:
-- users (1) -> doctors (0..1)           via doctors.user_id
-- users (1) -> patients (0..1)          via patients.user_id
-- users (1) -> family_members (N)       via family_members.user_id
-- doctors (1) -> patients (N)           via patients.assigned_doctor_id
-- users (1) -> user_settings (0..1)     via user_settings.user_id
-- users (1) -> notifications (N)        via notifications.user_id
-- users (1) -> audit_logs (N)           via audit_logs.user_id
--
-- Care workflow:
-- patients (1) -> training_sessions (N) via training_sessions.patient_id
-- training_sessions (1) -> recordings (N) via recordings.session_id
-- patients (1) -> recordings (N)        via recordings.patient_id
-- recordings (1) -> voice_assessments (N) via voice_assessments.recording_id
-- patients (1) -> mri_assessments (N)   via mri_assessments.patient_id
-- doctors (1) -> diagnoses (N)          via diagnoses.doctor_id
-- patients (1) -> diagnoses (N)         via diagnoses.patient_id
--
-- Clinical/ADNI:
-- patients (1) -> visits (N)            via visits.patient_id
-- visits (1) -> clinical_tests (N)      via clinical_tests.visit_id
-- visits (1) -> neuropsych_tests (N)    via neuropsych_tests.visit_id
-- visits (1) -> biomarkers (N)          via biomarkers.visit_id
-- visits (0..1) -> mri_assessments (0..1) via visits.mri_assessment_id
--
-- Family observations:
-- family_members (1) -> caregiver_observations (N) via caregiver_observations.family_member_id
-- patients (1) -> caregiver_observations (N) via caregiver_observations.patient_id
--
-- Storage and ingestion:
-- users (1) -> storage_objects (N)      via storage_objects.uploaded_by_user_id
-- patients (1) -> mri_files (N)         via mri_files.patient_id
-- visits (0..1) -> mri_files (N)        via mri_files.visit_id
--
-- Explicit storage foreign keys (for full relationship completeness):
-- ALTER TABLE recordings
--     ADD CONSTRAINT fk_recordings_storage_object
--     FOREIGN KEY (storage_object_id) REFERENCES storage_objects(id);
--
-- ALTER TABLE mri_assessments
--     ADD CONSTRAINT fk_mri_assessments_storage_object
--     FOREIGN KEY (storage_object_id) REFERENCES storage_objects(id);


-- ============================================================================
-- End of readable draft
-- ============================================================================
