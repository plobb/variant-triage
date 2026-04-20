# variant-triage

A **clinical-flavoured variant interpretation service** demonstrating production-grade
software engineering practices for a genetic diagnostics context.

> **This is a portfolio project using only synthetic data. See [CLINICAL_DISCLAIMER.md](CLINICAL_DISCLAIMER.md).**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         variant-triage                              │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │  Ingestion   │   │   Domain     │   │        API           │   │
│  │              │   │              │   │   (FastAPI / REST)   │   │
│  │  vcf_parser  │──▶│  VCFRecord   │──▶│                      │   │
│  │  (cyvcf2)    │   │  Variant     │   │  /variants           │   │
│  │              │   │  Classif..   │   │  /samples            │   │
│  └──────────────┘   └──────────────┘   │  /classifications    │   │
│                                        └──────────┬───────────┘   │
│  ┌──────────────────────────────────────┐          │               │
│  │           Persistence (SQLAlchemy 2) │◀─────────┘               │
│  │                                      │                          │
│  │  Sample ──< Variant ──< Classification                          │
│  │  AuditLog (append-only)              │                          │
│  └─────────────────┬────────────────────┘                          │
│                    │                                               │
│           ┌────────▼────────┐                                      │
│           │  PostgreSQL 16  │                                      │
│           └─────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key design decisions

| Concern | Choice | Rationale |
|---|---|---|
| Async runtime | asyncio + asyncpg | Non-blocking I/O for concurrent variant uploads |
| ORM | SQLAlchemy 2.0 (mapped_column) | Type-safe, modern declarative style |
| Validation | Pydantic v2 | Fast, strict, JSON-schema exportable |
| VCF parsing | cyvcf2 | htslib-backed, handles gVCF/multi-sample/long-read |
| Logging | structlog | Structured JSON in production, coloured in dev |
| Audit | SHA-256 payload hashing | Tamper-evident log for GxP / SOC2 scenarios |

---

## Quickstart

### Prerequisites

- Docker ≥ 24 and Docker Compose v2
- (Optional) Python 3.12 for local development

### Run with Docker Compose

```bash
git clone <repo>
cd variant-triage
cp .env.example .env
# Edit SECRET_KEY in .env

docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start Postgres separately (or use docker-compose up postgres)
cp .env.example .env && source .env

# Apply migrations
alembic upgrade head

# Run the server
uvicorn app.main:app --reload
```

---

## Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Type check (domain + ingestion modules)
mypy --strict app/domain/ app/ingestion/

# Lint
ruff check app/ tests/
```

---

## Project Roadmap

| Phase | Scope | Status |
|---|---|---|
| **1 — Foundation** | Project scaffold, domain models, VCF parser, DB schema, CI | ✅ Complete |
| **2 — API layer** | FastAPI routes for samples/variants/classifications, JWT auth | 🔲 Planned |
| **3 — ACMG engine** | Rule-based ACMG/AMP 2015 classifier, evidence scoring | 🔲 Planned |
| **4 — Annotation** | gnomAD AF lookup, ClinVar sync, VEP consequence annotation | 🔲 Planned |
| **5 — Reporting** | PDF/JSON clinical report generation, variant export (VCF/TSV) | 🔲 Planned |
| **6 — Observability** | Prometheus metrics, OpenTelemetry tracing, Grafana dashboards | 🔲 Planned |
| **7 — Compliance** | FHIR R4 export, audit log review UI, role-based access control | 🔲 Planned |
