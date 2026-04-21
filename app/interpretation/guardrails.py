from __future__ import annotations

import re

DISCLAIMER: str = (
    "RESEARCH USE ONLY. This interpretation is AI-generated and has "
    "not been validated for clinical use. It must be reviewed and "
    "approved by a qualified clinical geneticist before any clinical "
    "application. This tool is not a medical device."
)

_FLAG_WARNING: str = (
    "\n\n⚠️ Note: This interpretation was flagged for review. "
    "Please verify all clinical claims before use."
)


class GuardrailChecker:
    FORBIDDEN_PATTERNS: list[str] = [
        r"you (have|has|suffer|are diagnosed)",
        r"(start|begin|take|prescribe|administer)\s+\w+",
        r"(definitely|certainly|absolutely)\s+(pathogenic|benign|causal)",
        r"(do not|don't|avoid)\s+(take|use|prescribe)",
        r"cancer\s+(diagnosis|confirmed|detected)",
    ]

    def check(self, text: str) -> list[str]:
        flags: list[str] = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(f"Flagged pattern: {pattern}")
        return flags

    def sanitize(self, text: str) -> str:
        if self.check(text):
            return text + _FLAG_WARNING
        return text
