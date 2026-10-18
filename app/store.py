import json
import sqlite3
from pathlib import Path
from threading import RLock


class Store:
    def __init__(self, path):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                seq INTEGER NOT NULL, data TEXT NOT NULL, UNIQUE(run_id,seq));
            CREATE TABLE IF NOT EXISTS ledger (run_id TEXT, order_id TEXT, amount INTEGER NOT NULL,
                PRIMARY KEY(run_id,order_id));
            CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
        """)

    def put_run(self, run):
        with self.lock, self.db:
            self.db.execute("INSERT INTO runs VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (run["id"], json.dumps(run)))

    def run(self, run_id):
        with self.lock:
            row = self.db.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def runs(self):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute("SELECT data FROM runs ORDER BY rowid DESC LIMIT 30")]

    def events(self, run_id):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute("SELECT data FROM events WHERE run_id=? ORDER BY seq", (run_id,))]

    def local_memories(self, category, mode):
        with self.lock:
            rows = self.db.execute("SELECT data FROM events ORDER BY rowid DESC LIMIT 100").fetchall()
        hits = []
        for row in rows:
            e = json.loads(row[0])
            if e["case"]["category"] == category and not e["monitor"]["allowed"] and e["mode"] == mode:
                hits.append({"id": e["id"], "text": "Prior %s incident blocked by %s" % (category, ", ".join(e["monitor"]["rules"]))})
        return hits[:3]

    def commit_event(self, event):
        # Ledger execution and event persistence share a transaction. A duplicate
        # order cannot execute twice, even if callers replay the same proposal.
        with self.lock, self.db:
            if event["executed_cents"]:
                self.db.execute("INSERT INTO ledger VALUES (?,?,?)", (event["run_id"], event["case"]["order"]["id"], event["executed_cents"]))
            self.db.execute("INSERT INTO events VALUES (?,?,?,?)", (event["id"], event["run_id"], event["seq"], json.dumps(event)))

    def update_event(self, event):
        with self.lock, self.db:
            self.db.execute("UPDATE events SET data=? WHERE id=?", (json.dumps(event), event["id"]))

    def attempts(self):
        with self.lock:
            row = self.db.execute("SELECT value FROM counters WHERE name='claude_attempts'").fetchone()
            return row[0] if row else 0

    def reserve_attempt(self, limit):
        with self.lock, self.db:
            self.db.execute("INSERT INTO counters VALUES ('claude_attempts',0) ON CONFLICT(name) DO NOTHING")
            result = self.db.execute("UPDATE counters SET value=value+1 WHERE name='claude_attempts' AND value < ?", (limit,))
            return result.rowcount == 1
