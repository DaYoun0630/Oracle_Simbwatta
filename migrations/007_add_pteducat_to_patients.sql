-- Add ADNI PTEDUCAT (years of education) to patients
ALTER TABLE patients
ADD COLUMN IF NOT EXISTS pteducat SMALLINT NULL;

