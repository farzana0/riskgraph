"""Reproducible CLI evidence; no UI or credentials required for offline mode."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain import SUITES
from app.engine import Engine
from app.store import Store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--cases",type=int,default=40)
    parser.add_argument("--mode",choices=["offline","claude"],default="offline")
    parser.add_argument("--memory",action="store_true")
    parser.add_argument("--suite",choices=list(SUITES),default="baseline")
    parser.add_argument("--output",default="evidence/evaluation.json")
    args=parser.parse_args()
    if not 1<=args.cases<=200 or not 0<=args.seed<2**31:
        parser.error("Use 1–200 cases and a nonnegative 31-bit seed")
    if args.mode=="claude" and args.cases>40:
        parser.error("Claude evaluations are capped at 40 cases")
    # Live attempts must persist across CLI runs, too.
    store=Store(os.getenv("DATABASE_PATH","data/riskgraph.sqlite3") if args.mode=="claude" else ":memory:")
    engine=Engine(store)
    run=engine.create(args.seed,args.cases,args.mode,args.memory,suite=args.suite)
    for i in range(args.cases):
        engine.step(run["id"],i)
    result=engine.snapshot(run["id"])
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"mode":args.mode,"cases":result["gross"]["n"],"harmful_proposals":result["gross"]["failures"],"blocked":result["blocked"],"prevented_usd":result["prevented_usd"],"observed_residual_loss_usd":result["residual"]["observed_loss_usd"],"evidence":str(target)},indent=2))


if __name__=="__main__":main()
