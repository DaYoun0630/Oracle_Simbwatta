-- Core schema (simplified from architecture doc)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    google_id VARCHAR(255) UNIQUE,
    profile_picture VARCHAR(500),
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id),
    hospital VARCHAR(200),
    department VARCHAR(100),
    license_number VARCHAR(50),
    specialization VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id),
    date_of_birth DATE,
    phone VARCHAR(20),
    mci_stage VARCHAR(20),
    diagnosis_date DATE,
    assigned_doctor_id UUID REFERENCES doctors(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patients_doctor ON patients(assigned_doctor_id);

CREATE TABLE IF NOT EXISTS family_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    relationship VARCHAR(50),
    can_view_recordings BOOLEAN DEFAULT false,
    can_view_transcripts BOOLEAN DEFAULT true,
    can_view_scores BOOLEAN DEFAULT true,
    approved_by UUID REFERENCES doctors(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_family_patient ON family_members(patient_id);
CREATE INDEX IF NOT EXISTS idx_family_user ON family_members(user_id);

CREATE TABLE IF NOT EXISTS training_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    exercise_type VARCHAR(50),
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    conversation JSONB
);

CREATE INDEX IF NOT EXISTS idx_sessions_patient ON training_sessions(patient_id, started_at DESC);

CREATE TABLE IF NOT EXISTS recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    session_id UUID REFERENCES training_sessions(id),
    audio_path VARCHAR(500) NOT NULL,
    duration_seconds FLOAT,
    file_size_bytes BIGINT,
    format VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT NOW(),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_recordings_patient ON recordings(patient_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings(status) WHERE status != 'completed';

CREATE TABLE IF NOT EXISTS voice_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id UUID REFERENCES recordings(id),
    transcript TEXT,
    cognitive_score FLOAT,
    mci_probability FLOAT,
    flag VARCHAR(20) DEFAULT 'normal',
    flag_reasons JSONB,
    features JSONB,
    model_version VARCHAR(50),
    assessed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_recording ON voice_assessments(recording_id);
CREATE INDEX IF NOT EXISTS idx_assessments_flag ON voice_assessments(flag) WHERE flag != 'normal';

CREATE TABLE IF NOT EXISTS mri_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    scan_date TIMESTAMP,
    file_path VARCHAR(500),
    classification VARCHAR(20),
    probabilities JSONB,
    confidence FLOAT,
    model_version VARCHAR(50),
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mri_patient ON mri_assessments(patient_id, scan_date DESC);

CREATE TABLE IF NOT EXISTS diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES doctors(id),
    diagnosis_date TIMESTAMP DEFAULT NOW(),
    mci_stage VARCHAR(20),
    confidence VARCHAR(20),
    based_on_mri UUID REFERENCES mri_assessments(id),
    based_on_voice UUID REFERENCES voice_assessments(id),
    notes TEXT,
    follow_up_date DATE
);

CREATE INDEX IF NOT EXISTS idx_diagnoses_patient ON diagnoses(patient_id, diagnosis_date DESC);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    related_patient_id UUID REFERENCES patients(id),
    related_type VARCHAR(50),
    related_id UUID,
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, is_read, created_at DESC) 
WHERE is_read = false;

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500),
    accuracy FLOAT,
    notes TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
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

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
