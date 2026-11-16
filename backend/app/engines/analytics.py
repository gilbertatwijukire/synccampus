"""Leadership indicators (report section 4.6.5)."""
from collections import Counter


def _hours(a, b):
    return (b - a).total_seconds() / 3600


def summarise(concerns, now):
    open_c = [c for c in concerns if c.status not in ("resolved", "closed")]
    resolved = [c for c in concerns if c.resolved_at]
    first = [_hours(c.created_at, c.first_response_at) for c in concerns if c.first_response_at]
    res = [_hours(c.created_at, c.resolved_at) for c in resolved]
    by_cat = Counter(c.category.name for c in concerns)
    return {
        "total": len(concerns),
        "open": len(open_c),
        "critical_high": sum(1 for c in open_c if c.priority_level in ("Critical", "High")),
        "overdue": sum(1 for c in open_c if c.is_overdue),
        "avg_first_response_hrs": round(sum(first) / len(first), 1) if first else None,
        "avg_resolution_hrs": round(sum(res) / len(res), 1) if res else None,
        "resolution_rate": round(100 * len(resolved) / len(concerns)) if concerns else 0,
        "reopen_rate": round(100 * sum(1 for c in concerns if c.reopened_count) / len(resolved)) if resolved else 0,
        "by_category": dict(by_cat.most_common()),
    }
