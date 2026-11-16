"""Student-facing endpoints. No account: a reference number plus a private access code (like YOUR VOICE)."""
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Concern, Category, ConcernUpdate, Assignment, Delegate, User, now
from ..schemas import ConcernIn, TrackIn, ConfirmIn, AddInfoIn
from ..security import hash_code
from .. import services
import hmac

router = APIRouter(prefix="/api", tags=["student"])
_attempts: dict[str, tuple[int, float]] = {}   # reference -> (wrong attempts, locked until)


def _load(db: Session, ref: str, code: str) -> Concern:
    key = ref.strip().upper()
    n, until = _attempts.get(key, (0, 0))
    if until > time.time():
        raise HTTPException(429, "Too many wrong codes. Please wait a minute and try again.")
    c = db.scalar(select(Concern).where(Concern.reference == key))
    if not c or not hmac.compare_digest(c.access_code_hash, hash_code(code)):
        n += 1
        _attempts[key] = (n, time.time() + 60 if n >= 5 else 0)
        raise HTTPException(404, "Reference or access code not recognised")
    _attempts.pop(key, None)
    return c


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "is_sensitive": c.is_sensitive} for c in db.scalars(select(Category))]


@router.post("/concerns", status_code=201)
def submit(data: ConcernIn, db: Session = Depends(get_db)):
    try:
        c, code, matches = services.create_concern(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"reference": c.reference, "access_code": code, "is_public": c.is_public,
            "note": "Save your access code now. It is shown once and cannot be recovered.",
            "similar_reports_found": len(matches)}


@router.post("/track")
def track(body: TrackIn, db: Session = Depends(get_db)):
    c = _load(db, body.reference, body.access_code)
    return {"reference": c.reference, "title": c.title, "description": c.description, "status": c.status,
            "category": c.category.name, "created_at": c.created_at.isoformat(),
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            "is_public": c.is_public, "reopened_count": c.reopened_count,
            "updates": [{"from": u.author_label, "message": u.message, "visibility": u.visibility,
                         "at": u.created_at.isoformat()} for u in c.updates if u.visibility != "internal"]}


@router.post("/track/info")
def add_info(body: AddInfoIn, db: Session = Depends(get_db)):
    c = _load(db, body.reference, body.access_code)
    db.add(ConcernUpdate(concern_id=c.id, author_label="Student", visibility="private", message=body.message))
    db.commit()
    return {"ok": True}


@router.post("/track/confirm")
def confirm(body: ConfirmIn, db: Session = Depends(get_db)):
    """Student says whether the resolution really addressed the concern."""
    c = _load(db, body.reference, body.access_code)
    if c.status != "resolved":
        raise HTTPException(400, "This concern has not been marked resolved yet")
    if body.resolved:
        c.status = "closed"
    else:
        c.status, c.resolved_at, c.is_overdue = "in_progress", None, False
        c.reopened_count += 1
        for a in c.assignments:
            if a.status == "completed":
                a.status, a.completed_at = "active", None
    if body.comment:
        db.add(ConcernUpdate(concern_id=c.id, author_label="Student", visibility="private", message=body.comment))
    services.rescore(db, c)
    db.commit()
    return {"status": c.status}


@router.get("/public/concerns")
def public_feed(limit: int = 100, db: Session = Depends(get_db)):
    """Only concerns the student chose to make public; never attachments, access codes or private replies."""
    rows = db.scalars(select(Concern).where(Concern.is_public == True).order_by(Concern.created_at.desc()).limit(min(limit, 100)))  # noqa: E712
    return [{"reference": c.reference, "title": c.title, "description": c.description, "campus": c.campus,
             "category": c.category.name, "status": c.status, "created_at": c.created_at.isoformat(),
             "public_replies": [{"from": u.author_label, "message": u.message} for u in c.updates if u.visibility == "public"]}
            for c in rows]


@router.get("/public/stats")
def public_stats(db: Session = Depends(get_db)):
    """Aggregate numbers for the home page. No titles, no private details; sensitive categories are left out of the breakdown."""
    all_c = db.scalars(select(Concern)).all()
    done = [c for c in all_c if c.status in ("resolved", "closed")]
    open_c = [c for c in all_c if c.status not in ("resolved", "closed")]
    first = [(c.first_response_at - c.created_at).total_seconds() / 3600 for c in all_c if c.first_response_at]
    cats: dict[str, int] = {}
    for c in all_c:
        if not c.category.is_sensitive:
            cats[c.category.name] = cats.get(c.category.name, 0) + 1
    stages = {s: sum(1 for c in all_c if c.status == s) for s in ("new", "assigned", "in_progress", "resolved", "closed")}
    campuses: dict[str, int] = {}
    for c in all_c:
        campuses[c.campus or "Not stated"] = campuses.get(c.campus or "Not stated", 0) + 1
    return {"total": len(all_c), "open": len(open_c), "resolved": len(done),
            "resolution_rate": round(100 * len(done) / len(all_c)) if all_c else 0,
            "avg_first_response_hrs": round(sum(first) / len(first), 1) if first else None,
            "overdue_now": sum(1 for c in open_c if c.is_overdue),
            "overdue_pct": round(100 * sum(1 for c in open_c if c.is_overdue) / len(open_c)) if open_c else 0,
            "stages": stages, "campuses": campuses,
            "top_categories": sorted(cats.items(), key=lambda kv: -kv[1])[:5]}


@router.get("/cabinet")
def cabinet(db: Session = Depends(get_db)):
    """Who represents students. Names and areas only; no emails or phone numbers are exposed."""
    rows = db.scalars(select(Delegate).join(User).where(Delegate.show_public == True, User.is_active == True,  # noqa: E712
                                                          User.role.in_(("president", "delegate")))).all()
    out = [{"name": d.user.full_name, "title": d.portfolio, "is_president": d.user.role == "president",
            "bring_to_them": [x.strip() for x in d.categories_handled.split(",") if x.strip() and x.strip().lower() != "general"]}
           for d in rows]
    return sorted(out, key=lambda x: (not x["is_president"], x["name"]))
