"""Reminder / escalation rules (report section 4.6.4)."""
from .. import config


def evaluate(level: str, hours_open: float, has_reminder: bool, has_escalation: bool):
    """Return 'escalation', 'reminder' or None for an unresolved concern."""
    t = config.ESCALATION_HOURS[level]
    if hours_open >= t["escalate"] and not has_escalation:
        return "escalation"
    if hours_open >= t["reminder"] and not has_reminder and not has_escalation:
        return "reminder"
    return None
