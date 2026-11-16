"""Business logic shared by the routers."""
import json
from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from . import config
from .engines import priority, similarity, recommender, escalation
from .models import (Concern, Category, Delegate, Assignment, RelatedGroup, EscalationEvent,
                     AuditLog, User, ConcernUpdate, now)
from .security import new_access_code, new_reference, hash_code

OPEN = ("new", "assigned", "in_progress")


def audit(db: Session, user, action: str, entity: str, entity_id=None):
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity, entity_id=entity_id))


def related_count(db: Session, c: Concern) -> int:
    if not c.group_id:
        return 0
    g = db.get(RelatedGroup, c.group_id)
    return max(g.reports_count - 1, 0)


def rescore(db: Session, c: Concern):
    hours = (now() - c.created_at).total_seconds() / 3600
    score, level, _ = priority.compute_priority(
        base_severity=c.category.base_severity, urgency=c.urgency,
        students_affected=c.students_affected, hours_open=hours, response_limit_hrs=config.RESPONSE_LIMIT_HRS,
        related_reports=related_count(db, c), safety_flag=c.safety_flag)
    c.priority_score, c.priority_level = score, level
    return score, level


def explain_priority(db: Session, c: Concern):
    hours = (now() - c.created_at).total_seconds() / 3600
    return priority.compute_priority(
        base_severity=c.category.base_severity, urgency=c.urgency, students_affected=c.students_affected,
        hours_open=hours, response_limit_hrs=config.RESPONSE_LIMIT_HRS, related_reports=related_count(db, c),
        safety_flag=c.safety_flag)[2]


def create_concern(db: Session, data) -> tuple[Concern, str, list]:
    cat = db.get(Category, data.category_id)
    if not cat:
        raise ValueError("Unknown category")
    code = new_access_code()
    c = Concern(reference=new_reference(), access_code_hash=hash_code(code), title=data.title.strip(),
                description=data.description.strip(), category_id=cat.id, campus=data.campus, location=data.location,
                urgency=data.urgency, safety_flag=data.safety_flag, students_affected=data.students_affected,
                is_public=False if cat.is_sensitive else data.is_public)   # sensitive categories are always private
    db.add(c); db.flush()
    c.category = cat

    # related-concern detection within the same category (open or recently created)
    since = now() - timedelta(days=30)
    others = db.scalars(select(Concern).where(Concern.category_id == cat.id, Concern.id != c.id,
                                              Concern.created_at >= since, Concern.status != "closed")).all()
    matches = similarity.find_related(f"{c.title}. {c.description}",
                                      [(o.id, f"{o.title}. {o.description}") for o in others],
                                      c.location, {o.id: o.location for o in others})
    if matches:
        best = db.get(Concern, matches[0][0])
        if best.group_id:
            g = db.get(RelatedGroup, best.group_id); g.reports_count += 1
        else:
            g = RelatedGroup(master_concern_id=best.id, reports_count=2); db.add(g); db.flush()
            best.group_id = g.id
        c.group_id = g.id
        for member in db.scalars(select(Concern).where(Concern.group_id == g.id)).all():
            rescore(db, member)                       # repeated reports raise priority for every member
    rescore(db, c)
    db.commit()
    return c, code, matches


def delegate_pool(db: Session, c: Concern):
    out = []
    for d in db.scalars(select(Delegate)).all():
        load = db.scalar(select(func.count()).select_from(Assignment).join(Concern).where(
            Assignment.delegate_id == d.id, Assignment.status == "active", Concern.status.in_(OPEN)))
        similar = db.scalar(select(func.count()).select_from(Assignment).join(Concern).where(
            Assignment.delegate_id == d.id, Assignment.status == "completed", Concern.category_id == c.category_id))
        out.append({"id": d.id, "name": d.user.full_name, "portfolio": d.portfolio,
                    "categories_handled": d.categories_handled, "category_name": c.category.name,
                    "open_load": load or 0, "max_open_load": d.max_open_load,
                    "resolved_similar": similar or 0, "is_available": d.is_available and d.user.is_active})
    return out


def recommend(db: Session, c: Concern):
    return recommender.rank_delegates(delegate_pool(db, c))


def assign(db: Session, c: Concern, delegate: Delegate, by: User) -> Assignment:
    ranked = recommend(db, c)
    top = ranked[0]["delegate_id"] if ranked else None
    mine = next((r["score"] for r in ranked if r["delegate_id"] == delegate.id), 0)
    for a in c.assignments:
        if a.status == "active":
            a.status = "reassigned"
    a = Assignment(concern_id=c.id, delegate_id=delegate.id, recommended_score=mine,
                   was_overridden=(top is not None and top != delegate.id), assigned_by=by.id)
    db.add(a)
    if c.status == "new":
        c.status = "assigned"
    audit(db, by, "assign", "concern", c.id)
    db.commit()
    return a


def run_escalation_checks(db: Session) -> list[dict]:
    """Create reminder / escalation events once per concern. Called by the scheduler and by an admin endpoint."""
    fired = []
    for c in db.scalars(select(Concern).where(Concern.status.in_(OPEN))).all():
        rescore(db, c)
        hours = (now() - c.created_at).total_seconds() / 3600
        types = {e.type for e in db.scalars(select(EscalationEvent).where(EscalationEvent.concern_id == c.id)).all()}
        action = escalation.evaluate(c.priority_level, hours, "reminder" in types, "escalation" in types)
        if action:
            reason = f"{c.priority_level} concern open {hours:.1f}h"
            db.add(EscalationEvent(concern_id=c.id, type=action, reason=reason))
            if action == "escalation":
                c.is_overdue = True
            fired.append({"concern": c.reference, "type": action, "reason": reason})
    db.commit()
    return fired


def build_handover(db: Session, term_label: str, by: User) -> dict:
    rows = []
    for c in db.scalars(select(Concern).where(Concern.status.in_(OPEN)).order_by(Concern.priority_score.desc())).all():
        a = next((x for x in c.assignments if x.status == "active"), None)
        rows.append({"reference": c.reference, "title": c.title, "category": c.category.name,
                     "priority": c.priority_level, "status": c.status, "overdue": c.is_overdue,
                     "assigned_to": a.delegate.user.full_name if a else None,
                     "created_at": c.created_at.isoformat(), "last_note": c.updates[-1].message if c.updates else None})
    return {"term": term_label, "generated_by": by.full_name, "generated_at": now().isoformat(),
            "open_concerns": rows, "count": len(rows)}
