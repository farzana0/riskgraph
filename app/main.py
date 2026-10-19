import hmac
import os
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from .engine import Engine, Busy, BudgetExceeded
from .providers import ProviderError
from .store import Store

STATIC = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    count: int = Field(default=40, ge=1, le=200)
    mode: Literal["offline", "claude"] = "offline"
    use_memory: bool = False


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_seq: int = Field(ge=0, le=200)


def create_app(db_path=None, seed_demo=True, agent=None, memory=None):
    app = FastAPI(title="RiskGraph", version="0.1.0")
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
        return {"status": "ok", "version": "0.1.0", "revision": os.getenv("RENDER_GIT_COMMIT", "local")}

    @app.get("/api/config")
    def config():
        return {"anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
                "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                "anthropic_workspace_selection": getattr(engine.agent, "workspace_source", "unselected"),
                "surreal_configured": engine.memory.configured,
                "operator_token_required": bool(token),
                "live_enabled": bool(token and os.getenv("ANTHROPIC_API_KEY")),
                "live_max_cases": 40, "synthetic_only": True,
                "claude_attempts_used": store.attempts(),
                "claude_attempts_limit": int(os.getenv("MAX_CLAUDE_CASES", "200"))}

    @app.get("/api/runs")
    def runs():
        return store.runs()

    @app.post("/api/runs", status_code=201)
    def new_run(body: RunRequest, request: Request, x_operator_token: Optional[str] = Header(default=None)):
        authorize(request, x_operator_token)
        if body.use_memory and engine.memory.configured and not token:
            raise HTTPException(503, "Hosted Agent Memory runs require a server operator token")
        if body.mode == "claude":
            if not token or not os.getenv("ANTHROPIC_API_KEY"):
                raise HTTPException(503, "Claude runs require a server API key and operator token")
            if body.count > 40:
                raise HTTPException(422, "Claude runs are capped at 40 cases per run")
        if len(store.runs()) >= 30:
            raise HTTPException(409, "This demo workspace has reached its 30-run limit. Export evidence and use a fresh database for another workspace.")
        run = engine.create(body.seed, body.count, body.mode, body.use_memory)
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

    @app.get("/api/runs/{run_id}/export")
    def export(run_id: str):
        try:
            data = engine.snapshot(run_id)
            return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="riskgraph-%s.json"' % run_id})
        except KeyError:
            raise HTTPException(404, "Run not found")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    if seed_demo and not store.runs():
        demo = engine.create(42, 40)
        for i in range(demo["count"]):
            engine.step(demo["id"], i)
    return app


app = create_app(seed_demo=os.getenv("RISKGRAPH_BOOTSTRAP", "true").lower() == "true")
