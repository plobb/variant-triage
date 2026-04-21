# Security Considerations

## Current Implementation (Portfolio/Research Use Only)

- JWT tokens expire in 30 minutes
- Passwords hashed with bcrypt (cost factor 12)
- Audit logging on all requests with SHA-256 payload hashing
- No real patient data — synthetic VCFs only
- [CLINICAL_DISCLAIMER.md](CLINICAL_DISCLAIMER.md) documents research-only status

---

## Requirements for Clinical/IVD Use (IVDR Compliance)

Software processing genetic variants for diagnostic purposes is regulated
under EU IVDR 2017/746 (and equivalent regulations in other jurisdictions).

- Software must be classified as IVD software under EU IVDR 2017/746
- CE marking required for clinical diagnostic use
- Quality Management System (ISO 13485) required
- Clinical validation studies required (analytical and clinical performance)
- Risk management per ISO 14971
- Post-market surveillance plan required
- Software lifecycle per IEC 62304 (medical device software)
- Usability engineering per IEC 62366

---

## Requirements for GDPR Compliance

Genetic data is special-category data under GDPR Article 9.

- Data Processing Agreement with cloud provider required
- Patient data must be pseudonymised or anonymised at rest and in transit
- Right to erasure (Article 17) implementation required
- Data residency constraints (EU only for EU patients)
- DPO appointment may be required depending on processing scale
- Data Protection Impact Assessment (DPIA) required before processing
  genetic data at scale (GDPR Article 35)
- Processing of genetic data requires explicit consent or a legal basis
  under Article 9(2)

---

## Infrastructure Security Gaps (Current vs Production)

| Control | Current | Production Requirement |
|---|---|---|
| Rate limiting | None | Required (brute force, API abuse prevention) |
| IP allowlisting | None | Recommended for admin endpoints |
| Secret storage | Fly.io secrets | HSM or dedicated secrets manager (e.g. AWS KMS) |
| Audit log storage | Same DB as application | Separate, append-only, tamper-evident store |
| TLS | Fly.io managed | End-to-end with certificate pinning |
| Penetration testing | Not conducted | Required before go-live |
| Vulnerability scanning | Not configured | SAST/DAST in CI pipeline |
| Dependency scanning | Not configured | Automated CVE scanning (Dependabot/Snyk) |
| Backup/DR | Not configured | RTO/RPO defined, tested restore procedure |

---

## API Key Management

- `ANTHROPIC_API_KEY` and `ONCOKB_API_TOKEN` must **never** be committed to git
- Keys are stored as Fly.io secrets and injected at runtime
- Rotate keys regularly (quarterly minimum)
- Use separate keys for development and production environments
- Monitor API usage for anomalies

---

## LLM-Specific Security (Phase 6 Interpretation Assistant)

- All Claude API responses are passed through `GuardrailChecker` before
  being returned to callers
- Prompt injection risk: variant notes field is included in the prompt —
  in production, sanitise user-supplied text before inserting into prompts
- Model outputs carry a mandatory disclaimer and are never presented as
  clinical-grade results without human review
- No patient-identifiable information should be included in prompts sent
  to third-party LLM APIs
