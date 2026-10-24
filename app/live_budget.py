"""Live budget connection with bounded contention wait; archived callers stay frozen."""
import sqlite3
from threading import RLock
from .travel_calls import TravelBudget


class LiveBudget(TravelBudget):
    def __init__(self,path,max_usd=1.2,max_calls=256):
        # Keep BEGIN IMMEDIATE reservations atomic across connections. A contended
        # database must wait before failing closed, rather than charging a retry.
        self.db=sqlite3.connect(path,check_same_thread=False,timeout=30)
        self.lock=RLock()
        self.db.executescript('CREATE TABLE IF NOT EXISTS calls (key TEXT PRIMARY KEY, state TEXT, cost REAL, result TEXT); CREATE TABLE IF NOT EXISTS design (id INTEGER PRIMARY KEY, data TEXT);')
        self.max_usd,self.max_calls=max_usd,max_calls
