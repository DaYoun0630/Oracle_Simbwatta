# Deployment Compliance Checklist (ADNI / TalkBank)

This checklist is for deploying the `/hodu` project safely while respecting licensed datasets (e.g., ADNI, TalkBank).

## 1) Data removal (must-do before any public deployment)
- Remove all licensed data from local disk, MinIO, and DB backups.
- Remove any derived files that include ADNI/TalkBank identifiers, filenames, or metadata.

Suggested command:
```
ops/sanitize_local_data.sh
```

## 2) Storage & access controls
- MinIO buckets must not be public.
- Use VPN/WireGuard or private network only.
- Disable public presigned URL sharing for licensed data.

## 3) Git safety
- Ensure `.gitignore` excludes `minio-data/`, `data/`, `runtime/`, `db_backups/`, `exports/`, and `docker/.env`.
- Do not commit any raw/processed datasets or dumps.

## 4) Model safety
- If model weights were trained on licensed data, do **not** publish weights unless the license explicitly permits redistribution.
- Inference on synthetic data is fine; public release of weights requires license review.

## 5) UI / demos
- Use synthetic patients and synthetic media only.
- Remove any labels like `ADNI_###_S_####` from UI, logs, or exports.

## 6) External services
- Do not send TalkBank audio/transcripts to third‑party APIs unless non‑retention is contractually guaranteed.

## 7) Paper/publication obligations
- Follow ADNI acknowledgment rules and DPC submission requirements if publishing results.

