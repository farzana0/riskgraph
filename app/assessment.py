"""Stateless assessment of adjudicated, end-to-end system outcomes.

One row is one completed business episode, not one message or one agent.
No customer text, identifiers, or uploaded traces are accepted or persisted.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .risk import estimate, conditional_mean_sequence
from .domain import CAP


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    proposed_loss_cents: int = Field(ge=0)
    residual_loss_cents: int = Field(ge=0)

class AssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    outcomes: list[Outcome] = Field(min_length=1, max_length=2000)
    exposure_cap_cents: int = Field(ge=1, le=100_000_000)
    sampling: Literal["stress", "representative_fixed", "adaptive"] = "stress"

    @model_validator(mode="after")
    def bounded(self):
        if any(max(row.proposed_loss_cents, row.residual_loss_cents) > self.exposure_cap_cents for row in self.outcomes):
            raise ValueError("An observed loss exceeds the prespecified exposure cap; revise the loss model, never clip observations")
        return self


def assess(body: AssessmentRequest):
    cap = body.exposure_cap_cents
    scale = cap / CAP
    streams = {}
    for name, field in (("proposed", "proposed_loss_cents"), ("residual", "residual_loss_cents")):
        values = [getattr(row, field) for row in body.outcomes]
        # Ceil integer arithmetic: mapped losses can never understate an input.
        rounded = [(v * CAP + cap - 1) // cap for v in values]
        risk = estimate(rounded, delta=.025)
        for key in ("expected_loss_usd", "severity_mean_usd", "anytime_upper_usd", "hoeffding_upper_usd"):
            risk[key] *= scale
        for key in ("expected_loss_ci95", "prior_sensitivity_usd", "severity_band_upper_usd"):
            risk[key] = [x * scale for x in risk[key]]
        risk["observed_loss_usd"] = sum(values) / 100
        risk["empirical_mean_usd"] = sum(values) / len(values) / 100
        risk["confidence_sequence"] = None  # Use the explicit target below.
        risk["conditional_mean_sequence"] = conditional_mean_sequence(values, cap, delta=.025)
        if body.sampling != "representative_fixed":
            risk["anytime_upper_usd"] = None
            risk["hoeffding_upper_usd"] = None
        risk["bound_assumption"] = "Fixed conditional tail probabilities; prespecified cap $%g; 2.5%% per stream" % (cap/100)
        risk["posterior_scope"] = "Descriptive frequency/severity model; extrapolation needs representative, stable sampling"
        streams[name] = risk
    return {"version": "assessment_v2", "episodes": len(body.outcomes), "sampling": body.sampling,
            "execution_loss_increases": sum(row.residual_loss_cents > row.proposed_loss_cents for row in body.outcomes),
            "exposure_cap_usd": cap / 100, **streams,
            "guarantee": "Both running-average conditional-mean intervals cover simultaneously over time with probability at least 95%, for bounded adapted losses and a cap fixed before observation. They do not bound the next episode or future workload.",
            "privacy": "Numeric outcomes only; request is not stored in the evaluation database",
            "unit": "One independently adjudicated business episode; agents within an episode may be dependent",
            "rounding_max_usd": scale / 100,
            "forecast_scope": "Posterior intervals describe mean upward-binned loss, not a future aggregate loss, premium, VaR, or expected shortfall"}
