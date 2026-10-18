import os
os.environ["DATABASE_PATH"] = ":memory:"
os.environ["RISKGRAPH_BOOTSTRAP"] = "false"

import pytest
from app.domain import Case, Order


@pytest.fixture
def case():
    return Case(id="c1", category="ordinary", customer="alice", order=Order(id="o1", owner="alice", paid_cents=10000, age_days=10), requested_cents=10000, message="Refund please")
