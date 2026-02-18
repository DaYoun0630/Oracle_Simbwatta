-- Add SHAP explainability columns for voice assessments.
-- Safe to run multiple times.

ALTER TABLE IF EXISTS voice_assessments
    ADD COLUMN IF NOT EXISTS shap_available BOOLEAN DEFAULT FALSE;

ALTER TABLE IF EXISTS voice_assessments
    ADD COLUMN IF NOT EXISTS shap_top_features JSONB;

ALTER TABLE IF EXISTS voice_assessments
    ADD COLUMN IF NOT EXISTS shap_feature_contributions JSONB;

ALTER TABLE IF EXISTS voice_assessments
    ADD COLUMN IF NOT EXISTS shap_meta JSONB;

