"""Workload-aware delegate recommendation (report section 4.6.3)."""
from .. import config


def category_match(delegate_categories: str, category_name: str) -> float:
    cats = [c.strip().lower() for c in delegate_categories.split(",") if c.strip()]
    if category_name.lower() in cats:
        return 1.0
    if "general" in cats:
        return 0.4
    return 0.0


def score_delegate(*, categories_handled, category_name, open_load, max_open_load, resolved_similar):
    M = category_match(categories_handled, category_name)
    L = min(open_load / max_open_load, 1) if max_open_load else 1
    E = min(resolved_similar / 10, 1)
    w = config.DELEGATE_WEIGHTS
    score = round(100 * (w["M"] * M + w["L"] * (1 - L) + w["E"] * E), 1)
    reasons = []
    reasons.append("area owner" if M == 1 else "general portfolio" if M > 0 else "no area match")
    reasons.append(f"load {open_load}/{max_open_load}")
    if resolved_similar:
        reasons.append(f"{resolved_similar} similar resolved")
    return score, {"M": M, "L": round(L, 2), "E": round(E, 2)}, reasons


def rank_delegates(delegates):
    """delegates: list of dicts with keys id, name, categories_handled, open_load, max_open_load,
    resolved_similar, is_available; plus category_name. Unavailable / full delegates are excluded."""
    ranked = []
    for d in delegates:
        if not d["is_available"] or d["open_load"] >= d["max_open_load"]:
            continue
        s, f, reasons = score_delegate(categories_handled=d["categories_handled"], category_name=d["category_name"],
                                       open_load=d["open_load"], max_open_load=d["max_open_load"],
                                       resolved_similar=d["resolved_similar"])
        ranked.append({"delegate_id": d["id"], "name": d["name"], "portfolio": d.get("portfolio", ""),
                       "score": s, "factors": f, "reasons": reasons})
    return sorted(ranked, key=lambda x: -x["score"])
