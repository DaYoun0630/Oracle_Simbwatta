# MCI Multimodal Platform (Portfolio)

Raspberry Pi 5 + Docker 기반으로 구축한 멀티모달 인지평가 플랫폼입니다.  
음성 파이프라인과 MRI 파이프라인을 하나의 서비스로 통합해, 의료진/보호자/환자 워크플로우를 지원합니다.

## Project Summary
- 목표: 음성 + MRI 기반 MCI 평가 워크플로우를 실제 서비스 형태로 구현
- 환경: RPi5 NAS(OMV) + Docker Compose + FastAPI + Celery + PostgreSQL + MinIO + Vue
- 핵심: 비동기 파이프라인, 의료진 화면 연동, 저장소/DB 일관성, 운영 안정성

## My Role
- 시스템 아키텍처 설계 및 백엔드 구축 주도
- 멀티모달 파이프라인(음성/MRI) 설계 및 연결
- 비동기 처리(Celery + Redis)와 저장 계층(PostgreSQL + MinIO) 통합
- 저사양 환경 최적화(zram + swap + 워커 튜닝)로 협업 가능한 개발 인프라 제공

## Key Contributions
1. End-to-End MRI Pipeline
- 입력 등록(`mri_assessments`) → Celery 큐 → ANTs 기반 전처리 → 모델 추론 → XAI 산출물 저장
- 결과 저장 위치 분리: 원본/전처리/XAI 버킷
- 환자별 최신 MRI 상태 조회 API와 프론트 연결

2. Voice Pipeline Integration
- 업로드/텍스트 연동/피처 추출/추론/결과 저장 자동화
- SHAP/XAI 결과 저장 및 조회 구조 반영
- 세션형 워크플로우와 DB 스키마 연동

3. 운영 안정화
- 워커 파라미터 보수화(`concurrency`, `prefetch`, thread 제한)
- 재시도/실패 상태 관리 및 로그 기반 트러블슈팅 루프 구축
- KST 기준 타임스탬프 일관성 정리

4. 데이터/컴플라이언스 가드
- 민감 데이터 경로 Git 제외 (`data/`, `minio-data/`, `runtime/`, `db_backups/`)
- 합성 데이터 기반 테스트 워크플로우 구축
- 라이선스 리스크 점검 체크리스트 반영

## Architecture
- Frontend: Vue 3 + Vite + Pinia
- API: FastAPI (`src/app`)
- Worker: Celery (`src/worker/tasks.py`)
- Queue: Redis
- DB: PostgreSQL 16
- Object Storage: MinIO
- Reverse Proxy: Nginx

## Service Map
- `mci-api`: 인증/환자/의료진/세션 API
- `mci-worker`: 음성/MRI 비동기 작업 처리
- `mci-postgres`: 임상/평가/파일 메타데이터 저장
- `mci-minio`: 파일 오브젝트 저장
- `mci-redis`: 태스크 브로커/백엔드
- `mci-nginx`: 정적 프론트 및 API 프록시

## Pipeline Overview
### MRI
1. MRI 소스 등록
2. Celery `process_mri_scan` 큐잉
3. 전처리(ANTs)
4. 추론/확률 계산
5. XAI(Grad-CAM/ROI) 산출
6. DB + MinIO 반영

### Voice
1. 음성/텍스트 업로드
2. 비동기 피처 추출
3. 모델 추론 + SHAP 결과 생성
4. DB 반영 및 화면 조회

## Outcomes
- 멀티모달 파이프라인의 서비스형 통합 완료
- 환자 단위 결과 조회/추적 가능한 데이터 구조 정립
- 저사양 환경에서도 동시 협업 가능한 운영 안정성 확보

## Repository Structure
- `src/app/`: FastAPI API 레이어
- `src/worker/`: Celery 태스크 및 모델 파이프라인
- `frontend/`: Vue 프론트엔드
- `docker/`: compose/env
- `migrations/`: DB 스키마/마이그레이션
- `scripts/`: 운영 보조 스크립트

## Run (Local)
```bash
cd docker
docker compose --env-file .env up -d
```

Frontend dev:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```

## Compliance Note
- 이 저장소는 원본 의료 데이터/식별자 공개를 금지합니다.
- 배포 전 합성 데이터만 남기고 민감 데이터(`data/raw`, `db_backups`, `exports`, MinIO 원본 버킷) 제거가 필요합니다.
- 외부 SaaS/LLM 연동 시 데이터 보존 정책을 반드시 검증합니다.

---
This README is intentionally portfolio-oriented: project scope, technical ownership, architecture, and delivery outcomes 중심으로 정리했습니다.
