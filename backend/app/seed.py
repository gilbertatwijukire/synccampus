"""Demo data: python -m app.seed"""
from .database import Base, engine, SessionLocal
from .models import User, Category, Delegate
from .security import hash_password

CATEGORIES = [  # name, base severity, sensitive?
    ("Academic issues", 0.60, False), ("Examinations", 0.80, False), ("Registration", 0.55, False),
    ("Timetables", 0.50, False), ("Tuition / fees", 0.65, False), ("ICT / Internet", 0.55, False),
    ("Campus facilities", 0.45, False), ("Security", 0.90, False), ("Student welfare", 0.60, False),
    ("Administration", 0.45, False), ("Student activities / events", 0.30, False),
    ("Harassment / discrimination", 0.95, True),
]
STAFF = [  # name, email, role, portfolio, categories handled
    ("Admin", "admin@saagi.local", "admin", "", ""),
    ("Guild President", "president@saagi.local", "president", "Guild President", "General"),
    ("A. Nakato", "nakato@saagi.local", "delegate", "Academic affairs", "Academic issues,Examinations,Timetables,Registration"),
    ("R. Okello", "okello@saagi.local", "delegate", "ICT minister", "ICT / Internet"),
    ("S. Kyomuhendo", "kyomuhendo@saagi.local", "delegate", "Finance liaison", "Tuition / fees,Administration"),
    ("J. Mukasa", "mukasa@saagi.local", "delegate", "Security & facilities", "Security,Campus facilities"),
    ("D. Lubega", "lubega@saagi.local", "delegate", "Welfare", "Student welfare,Student activities / events,Harassment / discrimination"),
]


def seed(db):
    if db.query(Category).count():
        return
    for n, s, sens in CATEGORIES:
        db.add(Category(name=n, base_severity=s, is_sensitive=sens))
    for name, email, role, portfolio, cats in STAFF:
        u = User(full_name=name, email=email, password_hash=hash_password("ChangeMe123!"), role=role)
        db.add(u); db.flush()
        if role in ("president", "delegate"):
            db.add(Delegate(user_id=u.id, portfolio=portfolio, categories_handled=cats, max_open_load=5))
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    print("Seeded. Staff logins use password: ChangeMe123!  (change immediately)")
