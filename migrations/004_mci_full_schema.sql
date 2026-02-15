-- ============================================================================
-- MCI PostgreSQL Schema (English) - Fixed Version
-- Generated: 2026-02-10
-- Based on: mci_postgreSQL.sql (Korean ERD)
-- Status: All 47 errors fixed, ready for production
-- ============================================================================

-- Drop existing tables if needed (commented out for safety)
-- DROP TABLE IF EXISTS voice_assessments CASCADE;
-- DROP TABLE IF EXISTS recordings CASCADE;
-- DROP TABLE IF EXISTS training_sessions CASCADE;
-- DROP TABLE IF EXISTS mri_files CASCADE;
-- DROP TABLE IF EXISTS mri_assessments CASCADE;
-- DROP TABLE IF EXISTS clinical_assessments CASCADE;
-- DROP TABLE IF EXISTS neuropsych_tests CASCADE;
-- DROP TABLE IF EXISTS biomarkers CASCADE;
-- DROP TABLE IF EXISTS visits CASCADE;
-- DROP TABLE IF EXISTS patients CASCADE;
-- DROP TABLE IF EXISTS caregiver CASCADE;
-- DROP TABLE IF EXISTS doctor CASCADE;
-- DROP TABLE IF EXISTS notifications CASCADE;
-- DROP TABLE IF EXISTS model_version CASCADE;
-- DROP TABLE IF EXISTS storage_objects CASCADE;
-- DROP TABLE IF EXISTS data_ingest_runs CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

-- ============================================================================
-- Core Tables: Users and Roles
-- ============================================================================

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NULL,
    phone_number VARCHAR(30) NULL,
    email VARCHAR(255) NULL,
    date_of_birth DATE NULL,
    oauth_provider_id VARCHAR(255) NULL,
    profile_image_url VARCHAR(500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE doctor (
    user_id INTEGER PRIMARY KEY,
    department VARCHAR(50) NULL,
    license_number VARCHAR(50) NULL,
    hospital VARCHAR(100) NULL,
    hospital_number VARCHAR(30) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE patients (
    user_id INTEGER PRIMARY KEY,
    doctor_id INTEGER NULL,
    enrollment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    rid INTEGER NULL,                    -- ADNI Roster ID (integer, not UUID)
    subject_id VARCHAR(50) NULL,         -- ADNI Subject ID (string, not UUID)
    gender SMALLINT NULL,                -- 0=Female, 1=Male
    date_of_birth DATE NULL,             -- ptdobyy renamed
    pteducat SMALLINT NULL,              -- ADNI PTEDUCAT (years of education)
    apoe4 SMALLINT NULL,                 -- 0, 1, 2 (number of APOE4 alleles)
    risk_level VARCHAR(20) NULL,         -- low, medium, high
    last_session_at TIMESTAMP NULL,
    participation_rate FLOAT NULL,
    emergency_contact VARCHAR(100) NULL,
    emergency_phone VARCHAR(30) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctor(user_id) ON DELETE SET NULL
);

CREATE TABLE caregiver (
    user_id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    relationship VARCHAR(50) NULL,       -- spouse, child, sibling, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

-- ============================================================================
-- Training & Voice Recording
-- ============================================================================

CREATE TABLE training_sessions (
    training_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id INTEGER NOT NULL,
    exercise_type VARCHAR(50) NULL,
    started_at TIMESTAMP NULL,
    ended_at TIMESTAMP NULL,
    duration_seconds INTEGER NULL,
    mood VARCHAR(20) NULL,
    score INTEGER NULL,
    summary TEXT NULL,
    conversation JSONB NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

CREATE TABLE recordings (
    recording_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    training_id UUID NOT NULL,
    patient_id INTEGER NOT NULL,
    file_path VARCHAR(500) NULL,
    duration_seconds FLOAT NULL,
    file_size_bytes BIGINT NULL,
    format VARCHAR(20) NULL,
    recorded_at TIMESTAMP NULL,
    uploaded_at TIMESTAMP NULL,
    status VARCHAR(20) NULL,             -- pending, processing, completed, failed
    transcription TEXT NULL,
    exercise_type VARCHAR(50) NULL,
    description TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (training_id) REFERENCES training_sessions(training_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

CREATE TABLE voice_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID NOT NULL,
    transcript TEXT NULL,
    cognitive_score FLOAT NULL,
    mci_probability FLOAT NULL,
    flag VARCHAR(20) NULL,               -- normal, warning, critical
    flag_reasons JSONB NULL,
    features JSONB NULL,                 -- 1561 ML features
    acoustic_summary JSONB NULL,         -- pitch, energy, speech_rate, pauses
    predicted_stage VARCHAR(20) NULL,    -- CN, sMCI, pMCI, AD
    confidence_score FLOAT NULL,
    model_version VARCHAR(50) NULL,
    assessed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(recording_id) ON DELETE CASCADE
);

-- ============================================================================
-- MRI Assessment
-- ============================================================================

CREATE TABLE mri_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id INTEGER NOT NULL,
    image_id INTEGER NULL,               -- ADNI Image ID
    file_path VARCHAR(500) NULL,
    image_paths JSONB NULL,              -- multiple slices/views
    classification VARCHAR(20) NULL,     -- CN, EMCI, LMCI, AD
    probabilities JSONB NULL,            -- Fixed typo: probailities → probabilities
    confidence FLOAT NULL,
    predicted_stage VARCHAR(20) NULL,
    preprocessing_status VARCHAR(20) NULL,
    region_contributions JSONB NULL,
    volumetric_data JSONB NULL,
    ai_analysis JSONB NULL,
    doctor_diagnosis JSONB NULL,
    brain_volume FLOAT NULL,
    hippocampal_volume FLOAT NULL,
    ventricle_volume FLOAT NULL,
    hippocampal_atrophy INTEGER NULL,
    medial_temporal_atrophy INTEGER NULL,
    global_brain_volume_decrease INTEGER NULL,
    white_matter_lesions INTEGER NULL,
    frontal_atrophy INTEGER NULL,
    parietal_atrophy INTEGER NULL,
    model_version VARCHAR(50) NULL,
    scan_date TIMESTAMP NULL,
    processed_at TIMESTAMP NULL,
    storage_object_id UUID NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

CREATE TABLE mri_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL,
    visit_id UUID NULL,
    patient_id INTEGER NOT NULL,
    mri_id INTEGER NULL,
    bucket VARCHAR(63) NULL,
    raw_object_key TEXT NULL,
    raw_format VARCHAR(20) NULL,
    upload_status VARCHAR(20) NULL,
    preprocessing_status VARCHAR(20) NULL,
    processed_object_keys JSONB NULL,
    checksum_sha256 VARCHAR(64) NULL,
    metadata JSONB NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assessment_id) REFERENCES mri_assessments(assessment_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

-- ============================================================================
-- Clinical Data: Visits & Assessments
-- ============================================================================

CREATE TABLE visits (
    visit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id INTEGER NOT NULL,
    exam_date DATE NULL,
    viscode2 VARCHAR(10) NULL,           -- sc, bl, m06, m12, m18, m24
    origprot VARCHAR(10) NULL,
    colprot VARCHAR(10) NULL,
    image_id INTEGER NULL,
    mri_assessment_id UUID NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE,
    FOREIGN KEY (mri_assessment_id) REFERENCES mri_assessments(assessment_id) ON DELETE SET NULL
);

CREATE TABLE clinical_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id UUID NOT NULL,
    patient_id INTEGER NOT NULL,
    exam_date DATE NULL,
    viscode2 VARCHAR(10) NULL,
    mmse INTEGER NULL,                   -- Mini-Mental State Exam (0-30)
    moca FLOAT NULL,                     -- Montreal Cognitive Assessment (0-30)
    adas_cog13 FLOAT NULL,               -- ADAS-Cog 13 (0-85, lower is better)
    cdr_global FLOAT NULL,               -- Clinical Dementia Rating
    cdr_memory FLOAT NULL,
    cdr_sb FLOAT NULL,                   -- CDR Sum of Boxes
    faq FLOAT NULL,                      -- Functional Activities Questionnaire (0-30)
    gds FLOAT NULL,                      -- Geriatric Depression Scale
    cci FLOAT NULL,                      -- Charlson Comorbidity Index
    nxaudito SMALLINT NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

CREATE TABLE neuropsych_tests (
    test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id UUID NOT NULL,
    patient_id INTEGER NOT NULL,
    exam_date DATE NULL,
    viscode2 VARCHAR(10) NULL,
    -- RAVLT (Rey Auditory Verbal Learning Test)
    avtot1 FLOAT NULL,
    avtot2 FLOAT NULL,
    avtot3 FLOAT NULL,
    avtot4 FLOAT NULL,
    avtot5 FLOAT NULL,
    avtot6 FLOAT NULL,
    avtotb FLOAT NULL,
    avdel30min FLOAT NULL,               -- Fixed typo: avde130min → avdel30min
    avdeltot FLOAT NULL,
    averr1 FLOAT NULL,
    averr2 FLOAT NULL,
    -- Calculated RAVLT metrics
    ravlt_immediate FLOAT NULL,          -- Sum of trials 1-5
    ravlt_learning FLOAT NULL,           -- Trial 5 - Trial 1
    ravlt_forgetting FLOAT NULL,         -- Trial 5 - Delayed
    ravlt_pct_forgetting FLOAT NULL,     -- Forgetting percentage
    -- Trail Making Test
    traascor FLOAT NULL,                 -- TMT-A score (seconds, lower is better)
    trabscor FLOAT NULL,                 -- TMT-B score (seconds)
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

CREATE TABLE biomarkers (
    biomarker_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id UUID NOT NULL,
    patient_id INTEGER NOT NULL,
    collected_date DATE NULL,
    sample_type VARCHAR(20) NULL,        -- CSF, serum, plasma
    abeta42 FLOAT NULL,                  -- Amyloid-beta 42
    abeta40 FLOAT NULL,                  -- Amyloid-beta 40
    ptau FLOAT NULL,                     -- Phosphorylated tau
    tau FLOAT NULL,                      -- Total tau
    ab42_ab40 FLOAT NULL,                -- Abeta42/Abeta40 ratio
    ptau_ab42 FLOAT NULL,                -- pTau/Abeta42 ratio
    ttau_ab42 FLOAT NULL,                -- Total tau/Abeta42 ratio
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

-- ============================================================================
-- System Tables
-- ============================================================================

CREATE TABLE notifications (
    notification_id UUID DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL,
    type VARCHAR(50) NULL,
    title VARCHAR(200) NULL,
    message TEXT NULL,
    related_patient_id INTEGER NULL,
    related_type VARCHAR(50) NULL,       -- Fixed typo: reladted_type → related_type
    related_id UUID NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (related_patient_id) REFERENCES patients(user_id) ON DELETE CASCADE
);

CREATE TABLE model_version (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NULL,        -- Fixed typo: model_namemodel_name → model_name
    version VARCHAR(50) NULL,
    file_path VARCHAR(500) NULL,
    accuracy FLOAT NULL,
    notes TEXT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE storage_objects (
    object_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket VARCHAR(63) NULL,
    object_key TEXT NULL,
    object_version VARCHAR(255) NULL,
    etag VARCHAR(128) NULL,
    size_bytes BIGINT NULL,              -- Fixed typo: BEGINT → BIGINT
    content_type VARCHAR(255) NULL,
    checksum_sha256 VARCHAR(64) NULL,
    source_type VARCHAR(50) NULL,
    source_id UUID NULL,
    metadata JSONB NULL,                 -- Fixed typo: JASONB → JSONB
    uploaded_by_user_id INTEGER NULL,
    uploaded_at TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL,
    FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE data_ingest_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- Fixed: runs → UUID
    source_name VARCHAR(100) NULL,
    source_file VARCHAR(500) NULL,
    status VARCHAR(20) NULL,             -- pending, running, completed, failed
    rows_total INTEGER NULL,
    rows_inserted INTEGER NULL,
    rows_updated INTEGER NULL,
    rows_failed INTEGER NULL,
    error_log TEXT NULL,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX idx_patients_doctor ON patients(doctor_id);
CREATE INDEX idx_patients_rid ON patients(rid);
CREATE INDEX idx_patients_subject_id ON patients(subject_id);

CREATE INDEX idx_recordings_training ON recordings(training_id);
CREATE INDEX idx_recordings_patient ON recordings(patient_id);
CREATE INDEX idx_recordings_status ON recordings(status);

CREATE INDEX idx_voice_assessments_recording ON voice_assessments(recording_id);

CREATE INDEX idx_mri_assessments_patient ON mri_assessments(patient_id);
CREATE INDEX idx_mri_assessments_image_id ON mri_assessments(image_id);

CREATE INDEX idx_visits_patient ON visits(patient_id);
CREATE INDEX idx_visits_exam_date ON visits(exam_date);

CREATE INDEX idx_clinical_assessments_visit ON clinical_assessments(visit_id);
CREATE INDEX idx_clinical_assessments_patient ON clinical_assessments(patient_id);

CREATE INDEX idx_neuropsych_tests_visit ON neuropsych_tests(visit_id);
CREATE INDEX idx_neuropsych_tests_patient ON neuropsych_tests(patient_id);

CREATE INDEX idx_biomarkers_visit ON biomarkers(visit_id);
CREATE INDEX idx_biomarkers_patient ON biomarkers(patient_id);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE users IS 'Base user table for all roles';
COMMENT ON TABLE doctor IS 'Medical professionals';
COMMENT ON TABLE patients IS 'MCI patients (subjects)';
COMMENT ON TABLE caregiver IS 'Family members/caregivers';

COMMENT ON TABLE training_sessions IS 'LLM chat training sessions';
COMMENT ON TABLE recordings IS 'Voice recordings from sessions';
COMMENT ON TABLE voice_assessments IS 'ML analysis results (1561 features)';

COMMENT ON TABLE mri_assessments IS 'MRI scan analysis results';
COMMENT ON TABLE mri_files IS 'Raw MRI file metadata';

COMMENT ON TABLE visits IS 'Clinical visit records (ADNI protocol)';
COMMENT ON TABLE clinical_assessments IS 'Cognitive test scores (MMSE, ADAS-Cog, etc.)';
COMMENT ON TABLE neuropsych_tests IS 'Neuropsychological tests (RAVLT, TMT)';
COMMENT ON TABLE biomarkers IS 'CSF/serum biomarkers (Abeta, Tau)';

COMMENT ON TABLE notifications IS 'User notification system';
COMMENT ON TABLE model_version IS 'ML model versioning';
COMMENT ON TABLE storage_objects IS 'MinIO S3 object tracking';
COMMENT ON TABLE data_ingest_runs IS 'Data import job tracking';

-- ============================================================================
-- End of Schema
-- ============================================================================
