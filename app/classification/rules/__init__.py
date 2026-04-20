from app.classification.base import ACMGRule
from app.classification.rules.pm1 import PM1Rule
from app.classification.rules.pm2_ba1 import BA1Rule, PM2Rule
from app.classification.rules.pm4 import PM4Rule
from app.classification.rules.pp2_pp3_bp4 import BP4Rule, PP2Rule, PP3Rule
from app.classification.rules.ps1_pm5 import PM5Rule, PS1Rule
from app.classification.rules.pvs1 import PVS1Rule

__all__ = [
    "PVS1Rule",
    "PS1Rule",
    "PM5Rule",
    "PM1Rule",
    "PM2Rule",
    "BA1Rule",
    "PM4Rule",
    "PP2Rule",
    "PP3Rule",
    "BP4Rule",
    "DEFAULT_RULES",
]

DEFAULT_RULES: list[ACMGRule] = [
    PVS1Rule(),
    PS1Rule(),
    PM5Rule(),
    PM1Rule(),
    BA1Rule(),
    PM2Rule(),
    PM4Rule(),
    PP2Rule(),
    PP3Rule(),
    BP4Rule(),
]
