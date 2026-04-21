# variant-triage

A backend service for **variant classification and interpretation**, designed to model how clinical genomics workflows can be implemented as **reproducible, testable software systems**.

> **This is a portfolio project using only synthetic data. See [CLINICAL_DISCLAIMER.md](CLINICAL_DISCLAIMER.md).**

---

## Live Demo

- **API:** https://variant-triage.fly.dev  
- **Swagger UI:** https://variant-triage.fly.dev/docs  
- **Health check:** https://variant-triage.fly.dev/health  

> Note: the app may take ~30 seconds to wake from cold start on the free tier.

---

## Overview

Variant interpretation is often performed through a combination of pipelines, scripts, and manual review.  
This project explores how that process can be expressed as a **structured application** with:

- deterministic classification logic  
- explicit data models  
- traceable decision-making  
- a consistent API surface  

The goal is to bridge the gap between **bioinformatics workflows** and **production-facing services** used in clinical or translational settings.

---

## What this demonstrates

- **End-to-end system design**  
  From VCF ingestion through to classification, interpretation, and API exposure  

- **Separation of concerns**  
  Clear boundaries between domain logic, persistence, and API layer  

- **Reproducibility and testability**  
  Deterministic classification logic with comprehensive test coverage  

- **Operational awareness**  
  Authentication, audit logging, and containerised deployment  

- **Extensibility**  
  Designed to support additional evidence sources and classification frameworks  

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         variant-triage                              │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐     │
│  │  Ingestion   │   │   Domain     │   │        API           │     │
│  │              │   │              │   │   (FastAPI / REST)   │     │
│  │  vcf_parser  │──▶│  VCFRecord   │──▶│                      │     │
│  │  (cyvcf2)    │   │  Variant     │   │  /variants           │     │
│  │              │   │  Classif..   │   │  /samples            │     │
│  └──────────────┘   └──────────────┘   │  /classifications    │     │
│                                        └──────────┬───────────┘     │
│  ┌──────────────────────────────────────┐          │                 │
│  │           Persistence (SQLAlchemy 2) │◀─────────┘                 │
│  │                                      │                            │
│  │  Sample ──< Variant ──< Classification                          │
│  │  AuditLog (append-only)              │                            │
│  └─────────────────┬────────────────────┘                            │
│                    │                                                 │
│           ┌────────▼────────┐                                        │
│           │  PostgreSQL 16  │                                        │
│           └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Design decisions

- **Classification logic implemented as pure functions**  
  Ensures deterministic behaviour and simplifies testing  

- **Audit logging with SHA-256 payload hashing**  
  Provides a tamper-evident record of requests and outputs  

- **Async database access (SQLAlchemy + asyncpg)**  
  Supports concurrent ingestion and API usage  

- **External data sources abstracted behind clients**  
  Allows mocking in tests and future substitution  

- **Strict validation via Pydantic v2**  
  Enforces schema consistency at API boundaries  

---

## Quickstart

### Prerequisites

- Docker ≥ 24 and Docker Compose v2  
- (Optional) Python 3.12 for local development  

---

### Run with Docker Compose

```bash
git clone <repo>
cd variant-triage
cp .env.example .env

# Set SECRET_KEY in .env

docker-compose up --build
```

API available at:

```
http://localhost:8000
```

---

### Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
source .env

alembic upgrade head

uvicorn app.api.main:app --reload
```

---

## Example request

```bash
curl https://variant-triage.fly.dev/health
```

---

## Testing

```bash
pytest tests/
pytest tests/ --cov=app --cov-report=term-missing

mypy --strict app/
ruff check app/ tests/
```

---

## Project roadmap

| Phase | Scope | Status |
|---|---|---|
| **1 — Foundation** | Models, VCF parser, DB schema, CI | ✅ Complete |
| **2 — API layer** | FastAPI routes, JWT auth, audit logging | ✅ Complete |
| **3 — ACMG engine** | Germline classification logic | ✅ Complete |
| **4 — Somatic** | AMP/ASCO/CAP tiering, evidence clients | ✅ Complete |
| **5 — Evidence** | External data integration (ClinVar, etc.) | ✅ Complete |
| **6 — LLM assistant** | Interpretation draft generation | ✅ Complete |
| **7 — Deployment** | Fly.io deploy, CI/CD, security docs | ✅ Complete |

---

## Notes

- This project is **not intended for clinical use**
- Designed to explore **engineering patterns in genomics software**
- Uses synthetic data only
