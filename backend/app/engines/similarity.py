"""Related-concern detection: TF-IDF + cosine similarity, pure Python (report section 4.6.2)."""
import math
import re
from collections import Counter
from .. import config

STOP = set("""a an the and or but of to in on at for from with by is are was were be been it its this that these those
i we you they he she my our your their me us them there here very not no yes please have has had do does did can could
would should will just so as if than then too also about into out up down over under again still""".split())


# Small, editable synonym map so differently worded reports of the same problem still match.
SYNONYMS = {
    "wifi": "network", "internet": "network", "connection": "network", "connect": "network", "online": "network",
    "broken": "fault", "damaged": "fault", "faulty": "fault", "failing": "fault", "failed": "fault",
    "down": "fault", "outage": "fault", "working": "fault", "work": "fault",
    "lecturer": "teacher", "tutor": "teacher", "instructor": "teacher",
    "fees": "tuition", "fee": "tuition", "payment": "tuition", "paid": "tuition",
    "exam": "examination", "exams": "examination", "examinations": "examination", "test": "examination",
}


def _stem(t: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(t) > 4 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def tokenize(text: str):
    text = text.lower().replace("wi-fi", "wifi").replace("wi fi", "wifi")
    out = []
    for t in re.findall(r"[a-z0-9]+", text):
        if t in STOP or len(t) < 2:
            continue
        t = SYNONYMS.get(t, SYNONYMS.get(_stem(t), _stem(t)))
        out.append(t)
    return out


def _vectors(docs):
    toks = [Counter(tokenize(d)) for d in docs]
    n = len(docs)
    df = Counter()
    for c in toks:
        df.update(c.keys())
    idf = {t: math.log((1 + n) / (1 + df[t])) + 1 for t in df}
    vecs = []
    for c in toks:
        v = {t: (1 + math.log(f)) * idf[t] for t, f in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs


def cosine(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def find_related(new_text: str, candidates, new_location="", locations=None):
    """candidates: list of (id, text). Returns [(id, score, label)] sorted best first.
    A shared, non-empty location adds a small boost (0.05)."""
    if not candidates:
        return []
    vecs = _vectors([new_text] + [t for _, t in candidates])
    out = []
    for (cid, _), v in zip(candidates, vecs[1:]):
        s = cosine(vecs[0], v)
        if new_location and locations and locations.get(cid, "").lower() == new_location.lower():
            s = min(1.0, s + 0.05)
        label = "duplicate" if s >= config.DUPLICATE_THRESHOLD else "related" if s >= config.RELATED_THRESHOLD else None
        if label:
            out.append((cid, round(s, 3), label))
    return sorted(out, key=lambda x: -x[1])
