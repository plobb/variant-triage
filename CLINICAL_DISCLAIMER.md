# Clinical Disclaimer

## Portfolio / Research Tool — Not for Clinical Use

This software is a **portfolio and research project** created to demonstrate
software engineering skills in the context of genetic diagnostics. It is **not**
a validated clinical decision-support tool.

- All variant data used during development is **entirely synthetic** (computationally
  generated). No real patient data has been used or is stored.
- Classification outputs are illustrative only and have **not** been validated
  against clinical ground truth.
- This tool has **not** undergone any clinical validation, analytical validation,
  or regulatory review.

## What Would Be Required for IVD / IVDR Compliance

If this system were to be used as an In Vitro Diagnostic (IVD) medical device under
the EU **IVDR 2017/746** or equivalent national frameworks, it would require, at
minimum:

| Requirement | Details |
|---|---|
| **Risk classification** | Determine Rule classification (likely Class C/D for companion diagnostics or rare disease) |
| **QMS** | ISO 13485-compliant Quality Management System |
| **Analytical validation** | Sensitivity, specificity, precision, reproducibility on reference materials |
| **Clinical validation** | Evidence of clinical benefit, outcome studies |
| **Intended purpose** | Precisely scoped IFU (Instructions for Use) |
| **Technical documentation** | Full design history file per Annex II/III |
| **Notified Body** | Conformity assessment by an EU Notified Body (Class C/D) |
| **UDI / EUDAMED** | Registration in European database |
| **Post-market surveillance** | Periodic safety update reports, vigilance reporting |
| **Software lifecycle** | IEC 62304 software development lifecycle documentation |
| **Cybersecurity** | Risk management per MDCG 2019-16 guidance |

For US FDA pathways, an equivalent process under **21 CFR Part 820** (QSR) and
likely **De Novo** or **PMA** submission would apply.

---

*This disclaimer must be retained in any derivative work or deployment of this codebase.*
