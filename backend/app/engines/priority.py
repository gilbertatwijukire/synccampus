"""Transparent weighted-sum priority score (report section 4.6.1)."""
from .. import config


def level_for(score: float) -> str:
    for floor, name in config.LEVEL_BANDS:
        if score >= floor:
            return name
    return "Low"


def priority_from_factors(S, U, N, D, R, safety_flag=False, weights=None):
    """All factors are already normalised to 0..1. Returns (score, level, breakdown)."""
    w = weights or config.WEIGHTS
    parts = {k: round(w[k] * v * 100, 2) for k, v in zip("SUNDR", (S, U, N, D, R))}
    score = round(sum(parts.values()), 1)
    if safety_flag and score < 80:      # safety rule: never below Critical
        score = 80.0
        parts["safety_rule"] = "raised to Critical band"
    return score, level_for(score), {"factors": {"S": S, "U": U, "N": N, "D": D, "R": R}, "points": parts}


def compute_priority(*, base_severity, urgency, students_affected, hours_open,
                     response_limit_hrs, related_reports, safety_flag=False):
    """Raw concern attributes -> normalised factors -> score."""
    S = min(max(base_severity, 0), 1)
    U = config.URGENCY_MAP.get(urgency, 0.5)
    N = min(students_affected / config.STUDENTS_CAP, 1)
    D = min(hours_open / response_limit_hrs, 1) if response_limit_hrs else 0
    R = min(related_reports / config.RELATED_CAP, 1)
    return priority_from_factors(S, U, N, D, R, safety_flag)
