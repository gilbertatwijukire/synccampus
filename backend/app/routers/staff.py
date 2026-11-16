"""Guild President (triage + oversight) and delegate (handling) endpoints."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (Concern, Delegate, Assignment, ConcernUpdate, EscalationEvent, HandoverRecord, User, now)
from ..schemas import AssignIn, UpdateIn
from ..security import require_roles, current_user
from ..engines import analytics
from .. import services

router = APIRouter(prefix="/api", tags=["staff"])
leader = require_roles("president")   # system admins manage accounts and cannot open complaints
OPEN = services.OPEN


def _row(db, c: Concern):
    a = next((x for x in c.assignments if x.status == "active"), None)
    rec = services.recommend(db, c)[:1]
    return {"id": c.id, "reference": c.reference, "title": c.title, "category": c.category.name,
            "campus": c.campus, "location": c.location, "students_affected": c.students_affected,
            "priority_score": c.priority_score, "priority_level": c.priority_level, "status": c.status,
            "is_overdue": c.is_overdue, "age_hours": round((now() - c.created_at).total_seconds() / 3600, 1),
            "related_reports": services.related_count(db, c), "safety_flag": c.safety_flag,
            "assigned_to": a.delegate.user.full_name if a else None,
            "recommended": rec[0] if rec and not a else None}


@router.get("/leader/queue")
def queue(db: Session = Depends(get_db), user: User = Depends(leader)):
    rows = db.scalars(select(Concern).where(Concern.status.in_(OPEN)).order_by(Concern.priority_score.desc())).all()
    services.audit(db, user, "view_queue", "concern"); db.commit()
    return [_row(db, c) for c in rows]


@router.get("/leader/concerns/{cid}")
def detail(cid: int, db: Session = Depends(get_db), user: User = Depends(leader)):
    c = db.get(Concern, cid)
    if not c:
        raise HTTPException(404, "Not found")
    services.audit(db, user, "view_concern", "concern", c.id); db.commit()
    related = db.scalars(select(Concern).where(Concern.group_id == c.group_id, Concern.id != c.id)).all() if c.group_id else []
    return {**_row(db, c), "description": c.description, "explanation": services.explain_priority(db, c),
            "recommendations": services.recommend(db, c),
            "related": [{"reference": r.reference, "title": r.title} for r in related],
            "updates": [{"from": u.author_label, "message": u.message, "visibility": u.visibility, "at": u.created_at.isoformat()} for u in c.updates],
            "escalations": [{"type": e.type, "reason": e.reason, "at": e.triggered_at.isoformat()}
                            for e in db.scalars(select(EscalationEvent).where(EscalationEvent.concern_id == c.id))]}


@router.post("/leader/concerns/{cid}/assign")
def assign(cid: int, body: AssignIn, db: Session = Depends(get_db), user: User = Depends(leader)):
    c, d = db.get(Concern, cid), db.get(Delegate, body.delegate_id)
    if not c or not d:
        raise HTTPException(404, "Concern or delegate not found")
    a = services.assign(db, c, d, user)
    return {"assignment_id": a.id, "was_overridden": a.was_overridden, "recommended_score": a.recommended_score}


@router.get("/leader/workload")
def workload(db: Session = Depends(get_db), user: User = Depends(leader)):
    out = []
    for d in db.scalars(select(Delegate)).all():
        load = db.scalar(select(func.count()).select_from(Assignment).join(Concern).where(
            Assignment.delegate_id == d.id, Assignment.status == "active", Concern.status.in_(OPEN)))
        out.append({"delegate_id": d.id, "name": d.user.full_name, "portfolio": d.portfolio,
                    "open": load or 0, "max": d.max_open_load})
    return out


@router.get("/leader/analytics")
def stats(db: Session = Depends(get_db), user: User = Depends(leader)):
    return analytics.summarise(db.scalars(select(Concern)).all(), now())


@router.post("/leader/run-escalation")
def run_now(db: Session = Depends(get_db), user: User = Depends(leader)):
    return services.run_escalation_checks(db)


@router.get("/leader/escalations")
def escalations(db: Session = Depends(get_db), user: User = Depends(leader)):
    rows = db.scalars(select(EscalationEvent).order_by(EscalationEvent.id.desc()).limit(50)).all()
    return [{"concern": db.get(Concern, e.concern_id).reference, "title": db.get(Concern, e.concern_id).title,
             "type": e.type, "reason": e.reason, "at": e.triggered_at.isoformat()} for e in rows]


@router.post("/leader/handover")
def make_handover(term: str, db: Session = Depends(get_db), user: User = Depends(leader)):
    snap = services.build_handover(db, term, user)
    db.add(HandoverRecord(term_label=term, snapshot=json.dumps(snap), generated_by=user.id))
    services.audit(db, user, "generate_handover", "handover"); db.commit()
    return snap


@router.get("/leader/handover")
def list_handover(db: Session = Depends(get_db), user: User = Depends(leader)):
    return [{"id": h.id, "term": h.term_label, "generated_at": h.generated_at.isoformat(), "snapshot": json.loads(h.snapshot)}
            for h in db.scalars(select(HandoverRecord).order_by(HandoverRecord.id.desc()))]


# ---------------- delegate workspace ----------------
@router.get("/delegate/concerns")
def my_concerns(db: Session = Depends(get_db), user: User = Depends(require_roles("delegate", "president"))):
    if not user.delegate:
        return []
    rows = db.scalars(select(Concern).join(Assignment).where(
        Assignment.delegate_id == user.delegate.id, Assignment.status == "active").order_by(Concern.priority_score.desc())).all()
    return [{**_row(db, c), "description": c.description} for c in rows]


@router.post("/delegate/concerns/{cid}/update")
def post_update(cid: int, body: UpdateIn, db: Session = Depends(get_db),
                user: User = Depends(require_roles("delegate", "president"))):
    c = db.get(Concern, cid)
    mine = c and user.delegate and any(a.delegate_id == user.delegate.id and a.status == "active" for a in c.assignments)
    if not mine and user.role != "president":
        raise HTTPException(403, "This concern is not assigned to you")
    if body.visibility not in ("public", "private", "internal"):
        raise HTTPException(400, "Invalid visibility")
    if c.category.is_sensitive and body.visibility == "public":
        raise HTTPException(400, "Sensitive concerns cannot have public replies")
    db.add(ConcernUpdate(concern_id=c.id, author_user_id=user.id, author_label=user.full_name,
                         visibility=body.visibility, message=body.message))
    if not c.first_response_at:
        c.first_response_at = now()
    if body.status == "in_progress":
        c.status = "in_progress"
    elif body.status == "resolved":
        c.status, c.resolved_at = "resolved", now()
        for a in c.assignments:
            if a.status == "active":
                a.status, a.completed_at = "completed", now()
    services.audit(db, user, "update_concern", "concern", c.id)
    db.commit()
    return {"status": c.status}
