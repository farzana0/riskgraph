import json
import hmac
import os
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse
from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from .engine import Engine, Busy, BudgetExceeded
from .providers import ProviderError, MODELS
from .assessment import AssessmentRequest, assess
from .protocol import verify_handoffs
from .store import Store
from .domain import SUITES
from .paired_demo import load_bundle, analyze as analyze_paired
from .paired_diagnostics import diagnostics as paired_diagnostics
from .review import verify_review
from .scenarios import DESCRIPTIONS, LABELS

STATIC = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    count: int = Field(default=40, ge=1, le=200)
    mode: Literal["offline", "claude"] = "offline"
    use_memory: bool = False
    model: Optional[Literal["claude-haiku-5-5", "claude-sonnet-5-5"]] = None
    advisory_critic: bool = False
    suite: Literal["baseline", "balanced", "adversarial", "boundary", "heavy_tail", "drift", "correlated", "full_stress", "random_stress", "identity", "manipulation", "payment_edges", "compound"] = "baseline"


class SavedReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, max_length=100, pattern=r"^scale-travel-[a-z_]+-[0-9]+$")


class TravelLiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: Literal["wrong_date", "wrong_traveller", "duplicate_booking", "stale_quote", "fee_total", "nonrefundable", "connection", "injected_instruction"] = "fee_total"
    model: Literal["claude-haiku-5-5", "claude-sonnet-5-5"] = "claude-haiku-5-5"
    seed: int = Field(default=2026102471, ge=0, le=2**31-1)


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_seq: int = Field(ge=0, le=200)


class PairedAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    admitted_ids: list[str] = Field(default_factory=list, max_length=240)
    weights: dict[str, float]
    a: float = Field(default=1, gt=0, le=100)
    b: float = Field(default=1, gt=0, le=100)
    split: Literal["heldout", "development", "recorded", "walkthrough"] = "heldout"


def create_app(db_path=None, seed_demo=True, agent=None, memory=None):
    app = FastAPI(title="RiskGraph", version="0.12.0")
    store = Store(db_path or os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3"))
    engine = Engine(store, agent, memory)
    app.state.engine = engine
    app.state.store = store
    token = os.getenv("RISKGRAPH_ADMIN_TOKEN", "")

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response

    def authorize(request, supplied):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin mutations are not permitted")
        if token and not hmac.compare_digest(supplied or "", token):
            raise HTTPException(401, "Operator authorization required. Verify access in Connections.")

    @app.post("/api/operator/verify")
    def verify_operator(request: Request, x_operator_token: Optional[str] = Header(default=None)):
        # Authentication check only: no provider calls, no ledger writes, no run.
        authorize(request, x_operator_token)
        return {"authorized": True, "token_required": bool(token)}

    @app.get("/healthz")
    def health():
        return {"status": "ok", "version": "0.12.0", "revision": os.getenv("RENDER_GIT_COMMIT", "local")}

    @app.get("/demo")
    def paired_demo():
        return FileResponse(STATIC / "demo.html")

    @app.get("/api/paired-demo")
    def paired_bundle():
        return load_bundle()

    @app.post("/api/paired-demo/analyze")
    def paired_analysis(body: PairedAnalysisRequest):
        try:
            return analyze_paired(load_bundle(), body.admitted_ids, body.weights, body.a, body.b, body.split)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.post("/api/paired-demo/diagnostics")
    def model_diagnostics(body: PairedAnalysisRequest):
        try:
            return paired_diagnostics(load_bundle(), body.admitted_ids, body.weights, body.a, body.b, body.split)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/api/config")
    def config():
        return {"anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
                "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                "models": MODELS,
                "anthropic_workspace_selection": getattr(engine.agent, "workspace_source", "unselected"),
                "surreal_configured": engine.memory.configured,
                "operator_token_required": bool(token),
                "live_enabled": bool(token and os.getenv("ANTHROPIC_API_KEY")),
                "live_max_cases": 40, "synthetic_only": True, "suites": SUITES,
                "framework_version": "risk_v2", "suite_descriptions": DESCRIPTIONS, "scenario_labels": LABELS,
                "claude_attempts_used": store.attempts(),
                "claude_attempts_limit": int(os.getenv("MAX_CLAUDE_CASES", "500"))}

    @app.get("/api/benchmarks")
    def benchmarks():
        path = STATIC.parents[1] / "docs" / "examples" / "framework-v2.json"
        if not path.is_file():
            return {"available": False}
        return {"available": True, "study": json.loads(path.read_text())}

    @app.get("/api/runs")
    def runs():
        return store.runs()

    @app.post("/api/assess")
    def assessment(body: AssessmentRequest):
        return assess(body)

    @app.get("/api/model-comparison")
    def comparison():
        path = Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "model-comparison.json"
        if not path.is_file():
            path = STATIC.parents[1] / "docs" / "examples" / "paired-models.json"
        if not path.is_file():
            return {"available": False}
        study = json.loads(path.read_text())
        analysis_path = STATIC.parents[1] / "docs" / "examples" / "paired-model-analysis.json"
        analysis = json.loads(analysis_path.read_text()) if analysis_path.is_file() else None
        if analysis and set(analysis["run_ids"]) != {cell["run_id"] for cell in study["cells"]}:
            analysis = None
        return {"available": True, "study": study, "analysis": analysis}

    @app.get("/api/assurance")
    def assurance_study():
        path = STATIC.parents[1] / "docs" / "examples" / "assurance-study.json"
        return {"available": True, "study": json.loads(path.read_text())} if path.is_file() else {"available": False}

    @app.get("/api/memory-study")
    def memory_study():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "memory-v3" / "study.json",
                      STATIC.parents[1] / "docs" / "examples" / "memory-v3.json"]
        path = next((p for p in candidates if p.is_file()), None)
        return {"available": True, "study": json.loads(path.read_text())} if path else {"available": False}

    @app.get("/api/memory-audit")
    def memory_audit():
        return json.loads((STATIC.parents[1] / "docs" / "examples" / "haiku-memory-autopsy.json").read_text())

    @app.get("/travel")
    def travel_demo():
        return FileResponse(STATIC / "travel.html")

    @app.get("/travel/compare")
    def travel_comparison():
        return FileResponse(STATIC / "travel-compare.html")

    @app.get("/api/travel-factorial")
    def travel_factorial():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "travel-factorial-v2" / "study.json",
                      STATIC.parents[1] / "docs" / "examples" / "travel-factorial.json"]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            return {"available": False}
        study = json.loads(path.read_text())
        from .travel_factorial_bounds import independent_bounds
        study["robust_analysis"] = independent_bounds(study)
        return {"available": True, "study": study}

    @app.get("/api/travel-study")
    def travel_study():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "travel-v1" / "study.json",
                      STATIC.parents[1] / "docs" / "examples" / "travel-v1.json"]
        path = next((p for p in candidates if p.is_file()), None)
        return {"available": True, "study": json.loads(path.read_text())} if path else {"available": False}

    @app.get("/api/travel-stress")
    def travel_stress():
        return json.loads((STATIC.parents[1] / "docs" / "examples" / "travel-stress.json").read_text())

    @app.get("/api/travel-scale")
    def travel_scale():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "travel-scale" / "study.json",
                      STATIC.parents[1] / "docs" / "examples" / "travel-scale.json"]
        path = next((p for p in candidates if p.is_file()), None)
        return {"available": True, "study": json.loads(path.read_text())} if path else {"available": False}

    @app.get("/api/travel-scale/responses")
    def travel_scale_archive():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "travel-scale" / "responses.jsonl.gz",
                      STATIC.parents[1] / "docs" / "examples" / "travel-scale-responses.jsonl.gz"]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            raise HTTPException(404, "The response archive is preparing")
        return FileResponse(path, media_type="application/gzip", filename="riskgraph-travel-responses.jsonl.gz")

    @app.post("/api/travel-live", status_code=202)
    def travel_start(body: TravelLiveRequest, request: Request, tasks: BackgroundTasks, x_operator_token: Optional[str] = Header(default=None)):
        if not token:
            raise HTTPException(403, "Live requests require configured operator access")
        authorize(request, x_operator_token)
        from . import travel_live
        try:
            jid = travel_live.start(body.family, body.model, body.seed)
            tasks.add_task(travel_live.run, jid)
            return {"id": jid, "status": "running"}
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/travel-review", status_code=202)
    def travel_review(body: SavedReviewRequest, request: Request, tasks: BackgroundTasks, x_operator_token: Optional[str] = Header(default=None)):
        if not token:
            raise HTTPException(403, "Live requests require configured operator access")
        authorize(request, x_operator_token)
        from . import travel_live
        try:
            jid = travel_live.start_review(body.case_id)
            tasks.add_task(travel_live.run_review, jid)
            return {"id": jid, "status": "reviewing"}
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.get("/api/travel-live")
    def travel_progress(run: Optional[str] = None):
        from . import travel_live
        try:
            return travel_live.read(run)
        except ValueError as exc:
            raise HTTPException(404, str(exc))

    @app.get("/api/memory-followup")
    def memory_followup():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "memory-v4" / "study.json",
                      STATIC.parents[1] / "docs" / "examples" / "memory-v4.json"]
        path = next((p for p in candidates if p.is_file()), None)
        return {"available": True, "study": json.loads(path.read_text())} if path else {"available": False}

    @app.get("/api/research-study")
    def research_study():
        candidates = [Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "research-v2" / "study.json",
                      STATIC.parents[1] / "docs" / "examples" / "research-v2.json"]
        path = next((p for p in candidates if p.is_file()), None)
        return {"available": True, "study": json.loads(path.read_text())} if path else {"available": False}

    @app.get("/api/hard-benchmark")
    def hard_benchmark(study: Literal["latest", "primary", "high_budget"] = "latest"):
        data = Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent
        examples = STATIC.parents[1] / "docs" / "examples"
        choices = {"primary": (data / "hard-benchmark.json", examples / "hard-benchmark.json"),
                   "high_budget": (data / "high-budget" / "hard-benchmark.json", examples / "hard-benchmark-high-budget.json")}
        studies = {}
        for name, paths in choices.items():
            path = next((p for p in paths if p.is_file()), None)
            if path:
                studies[name] = json.loads(path.read_text())
        selected = ("high_budget" if studies.get("high_budget", {}).get("status") == "complete" else "primary") if study == "latest" else study
        if selected not in studies:
            return {"available": False}
        return {"available": True, "study": studies[selected], "selected": selected,
                "studies": [{"id":name,"status":s["status"],"cases":len(s["cases"]),"max_tokens":s["design"]["settings"]["max_tokens"]} for name,s in studies.items()]}

    @app.get("/api/hard-benchmark/development")
    def hard_development():
        path = Path(os.getenv("DATABASE_PATH", "data/riskgraph.sqlite3")).parent / "hard-benchmark-development.json"
        if not path.is_file():
            path = STATIC.parents[1] / "docs" / "examples" / "hard-benchmark-development.json"
        return {"available": True, "study": json.loads(path.read_text())} if path.is_file() else {"available": False}

    @app.get("/api/operational")
    def operational_study():
        path = STATIC.parents[1] / "docs" / "examples" / "operational-outcomes.json"
        return {"available": True, "study": json.loads(path.read_text())} if path.is_file() else {"available": False}

    @app.get("/api/operational/example")
    def operational_example():
        path = STATIC.parents[1] / "docs" / "examples" / "execution-fault-episodes.json"
        return json.loads(path.read_text()) if path.is_file() else []

    @app.get("/api/policy-proof")
    def policy_proof():
        path = STATIC.parents[1] / "docs" / "examples" / "policy-smt.json"
        return {"available": True, "study": json.loads(path.read_text())} if path.is_file() else {"available": False}

    @app.get("/api/stress")
    def stress_results():
        path = STATIC.parents[1] / "docs" / "examples" / "failure-campaign.json"
        return {"available": True, "study": json.loads(path.read_text())} if path.is_file() else {"available": False}

    @app.post("/api/runs", status_code=201)
    def new_run(body: RunRequest, request: Request, x_operator_token: Optional[str] = Header(default=None)):
        authorize(request, x_operator_token)
        if body.advisory_critic and body.mode != "claude":
            raise HTTPException(422, "The second model reviewer requires Claude mode")
        if body.use_memory and engine.memory.configured and not token:
            raise HTTPException(503, "Hosted Agent Memory runs require a server operator token")
        if body.mode == "claude":
            if not token or not os.getenv("ANTHROPIC_API_KEY"):
                raise HTTPException(503, "Claude runs require a server API key and operator token")
            if body.count > 40:
                raise HTTPException(422, "Claude runs are capped at 40 cases per run")
        if len(store.runs()) >= 30:
            raise HTTPException(409, "This demo workspace has reached its 30-run limit. Export evidence and use a fresh database for another workspace.")
        run = engine.create(body.seed, body.count, body.mode, body.use_memory, suite=body.suite, model=body.model, advisory_critic=body.advisory_critic)
        return engine.snapshot(run["id"])

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        try:
            return engine.snapshot(run_id)
        except KeyError:
            raise HTTPException(404, "Run not found")

    @app.post("/api/runs/{run_id}/step")
    def step(run_id: str, body: StepRequest, request: Request, x_operator_token: Optional[str] = Header(default=None)):
        authorize(request, x_operator_token)
        try:
            return engine.step(run_id, body.expected_seq)
        except KeyError:
            raise HTTPException(404, "Run not found")
        except Busy as exc:
            raise HTTPException(409, str(exc))
        except BudgetExceeded:
            raise HTTPException(429, "Workspace Claude attempt budget reached. Export evidence and review provider usage before increasing the server limit.")
        except ProviderError as exc:
            detail = exc.diagnostic["message"] + " No case executed."
            if token and exc.operator_message:
                detail += " Provider detail (operator only): " + exc.operator_message
            raise HTTPException(502, detail)

    @app.get("/api/runs/{run_id}/verify")
    def verify_evidence(run_id: str):
        if store.run(run_id) is None:
            raise HTTPException(404, "Run not found")
        events = store.events(run_id)
        results = []
        for event in events:
            if "review" not in event:
                results.append({"event_id": event["id"], "status": "legacy_without_review"})
                continue
            try:
                valid = verify_review(event) and ("handoffs" not in event or verify_handoffs(event))
            except (ValueError, KeyError, TypeError):
                valid = False
            results.append({"event_id": event["id"], "status": "verified" if valid else "mismatch"})
        return {"run_id": run_id, "verified": sum(r["status"] == "verified" for r in results),
                "mismatches": sum(r["status"] == "mismatch" for r in results),
                "legacy": sum(r["status"] == "legacy_without_review" for r in results),
                "events": results,
                "scope": "Recomputed policy checks and evidence digest; no cryptographic identity or end-to-end formal proof"}

    @app.get("/api/runs/{run_id}/export")
    def export(run_id: str):
        try:
            data = engine.snapshot(run_id)
            return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="riskgraph-%s.json"' % run_id})
        except KeyError:
            raise HTTPException(404, "Run not found")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "home.html")

    @app.get("/workspace")
    def assessment_workspace():
        return FileResponse(STATIC / "index.html")

    @app.get("/study")
    def real_model_graphs(experiment: Literal["latest", "original", "memory-v3"] = "latest"):
        return FileResponse(STATIC / ("research.html" if experiment == "original" else "memory-study.html"))

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    if seed_demo and not store.runs():
        demo = engine.create(42, 40)
        for i in range(demo["count"]):
            engine.step(demo["id"], i)
    return app


app = create_app(seed_demo=os.getenv("RISKGRAPH_BOOTSTRAP", "true").lower() == "true")
