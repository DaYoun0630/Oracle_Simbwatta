-- Clean up existing data
TRUNCATE TABLE voice_assessments, recordings, training_sessions, mri_assessments, neuropsych_tests, visits, biomarkers, clinical_assessments, patients, doctor, users CASCADE;

-- 1. Users
INSERT INTO users (user_id, email, name, oauth_provider_id, profile_image_url, created_at, updated_at) VALUES
(1, 'doctor@mci.com', 'Dr. Kim', 'google-doc-1', NULL, NOW(), NOW()),
(100, 'patient@mci.com', '김성신', 'google-pat-1', NULL, NOW(), NOW());

-- Reset sequence for users table to avoid collision on next insert
SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));

-- 2. Doctor
INSERT INTO doctor (user_id, hospital, license_number) VALUES
(1, '서울대학교병원', 'MD-12345');

-- 3. Patient
INSERT INTO patients (user_id, doctor_id, date_of_birth, gender, risk_level, rid, subject_id, created_at, updated_at) VALUES
(100, 1, '1948-01-01', 1, 'mid', 6726, '029_S_6726', NOW(), NOW());

-- 6. Visits (Must be inserted before assessments)
INSERT INTO visits (visit_id, patient_id, exam_date, viscode2, image_id, origprot, colprot, created_at) VALUES
('55555555-5555-5555-5555-555555555555', 100, '2019-07-29', 'sc', 1215729, 'ADNI3', 'ADNI3', NOW());

-- 4. Clinical Assessments
INSERT INTO clinical_assessments (
  assessment_id, visit_id, patient_id, exam_date, viscode2, mmse, moca, adas_cog13,
  cdr_global, cdr_memory, cdr_sb, faq, gds, cci, nxaudito, created_at
) VALUES
(gen_random_uuid(), '55555555-5555-5555-5555-555555555555', 100, '2019-07-29', 'sc', 30, 25.0, 7.33, 0.5, 0.5, 2.5, 9.0, 0.0, 38.0, 2, NOW());

-- 4-1. Neuropsych Tests
INSERT INTO neuropsych_tests (
  test_id, visit_id, patient_id, exam_date, viscode2,
  avtot1, avtot2, avtot3, avtot4, avtot5, avtot6, avtotb,
  avdel30min, avdeltot, averr1, averr2,
  ravlt_immediate, ravlt_learning, ravlt_forgetting, ravlt_pct_forgetting,
  traascor, trabscor, created_at
) VALUES (
  gen_random_uuid(), '55555555-5555-5555-5555-555555555555', 100, '2019-07-29', 'sc',
  6.0, 8.0, 11.0, 11.0, 12.0, 10.0, 8.0,
  8.0, 8.0, 2.0, 0.0,
  48.0, 6.0, 4.0, 33.33333333,
  36.0, 60.0, NOW()
);

-- 5. Biomarkers
INSERT INTO biomarkers (
  biomarker_id, visit_id, patient_id, collected_date, abeta42, abeta40, ptau, tau, ab42_ab40, ptau_ab42, ttau_ab42, created_at
) VALUES
(gen_random_uuid(), '55555555-5555-5555-5555-555555555555', 100, '2019-07-29', 1118.0, 15150.0, 13.63, 155.5, 0.07379538, 0.012191413, 0.139087657, NOW());

-- 7. MRI Assessments
INSERT INTO mri_assessments (assessment_id, patient_id, scan_date, classification, confidence, created_at) VALUES
(gen_random_uuid(), 100, '2019-07-29', 'LMCI', 0.85, NOW());

-- 8. Voice Data
INSERT INTO training_sessions (training_id, patient_id, started_at, ended_at, exercise_type) VALUES
('66666666-6666-6666-6666-666666666666', 100, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '10 minutes', 'daily_conversation');

INSERT INTO recordings (recording_id, training_id, patient_id, file_path, duration_seconds, recorded_at, status) VALUES
('77777777-7777-7777-7777-777777777777', '66666666-6666-6666-6666-666666666666', 100, 'voice/sample1.wav', 60, NOW() - INTERVAL '2 days', 'completed');

INSERT INTO voice_assessments (assessment_id, recording_id, assessed_at, cognitive_score, mci_probability, flag, transcript) VALUES
(gen_random_uuid(), '77777777-7777-7777-7777-777777777777', NOW() - INTERVAL '2 days', 75, 0.4, 'normal', '안녕하세요. 오늘 날씨가 참 좋네요.');
