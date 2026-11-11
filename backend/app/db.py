import json, sqlite3
from contextlib import contextmanager
from .config import DATA

@contextmanager
def connection():
    db = sqlite3.connect(DATA / "sessions.sqlite", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, role TEXT NOT NULL,
            profile TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
            questions TEXT NOT NULL DEFAULT '[]', summary TEXT)""")

def get(sid):
    with connection() as db:
        r = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not r: return None
    d=dict(r)
    for k in ('profile','questions','summary'):
        if d[k] is not None: d[k]=json.loads(d[k])
    return d

def save(s):
    with connection() as db:
        db.execute("UPDATE sessions SET questions=?, status=?, summary=? WHERE id=?",
            (json.dumps(s['questions']),s['status'],json.dumps(s['summary']) if s['summary'] else None,s['id']))
