"""Private, reviewed episode imports and explicit source-mixture sensitivity."""
import json
import os
from pathlib import Path
import re
from typing import Literal, Optional
from uuid import uuid4
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .travel import FAMILIES


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    event_id: str = Field(min_length=1, max_length=100)
    parent_ids: list[str] = Field(default_factory=list, max_length=20)
    actor: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=300)


class Episode(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    episode_id: str = Field(min_length=1, max_length=100)
    scenario: str = Field(min_length=1, max_length=100)
    reviewed: bool = False
    review_ref: Optional[str] = Field(default=None, max_length=200)
    potential_loss_cents: Optional[int] = Field(default=None, ge=0, le=1000000000)
    executed_loss_cents: Optional[int] = Field(default=None, ge=0, le=1000000000)
    events: list[TraceEvent] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def provenance(self):
        if self.reviewed and not self.review_ref:
            raise ValueError('A reviewed episode requires a review reference')
        ids = [x.event_id for x in self.events]
        if len(set(ids)) != len(ids): raise ValueError('Duplicate event ID')
        seen = set()
        for event in self.events:
            if any(parent not in seen for parent in event.parent_ids): raise ValueError('Parents must refer to earlier events in the same episode')
            seen.add(event.event_id)
        return self


class EvidenceBatch(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal['trace-evidence-v1'] = 'trace-evidence-v1'
    source: Literal['observed', 'simulation', 'illustration']
    system_version: str = Field(min_length=1, max_length=100)
    reference_configuration: str = Field(min_length=1, max_length=120)
    loss_cap_cents: int = Field(default=100000, ge=1, le=1000000000)
    episodes: list[Episode] = Field(min_length=1, max_length=256)

    @model_validator(mode='after')
    def check_batch(self):
        ids = [r.episode_id for r in self.episodes]
        if len(ids) != len(set(ids)): raise ValueError('Repeated episode IDs would inflate the evidence count')
        for r in self.episodes:
            if any(x is not None and x > self.loss_cap_cents for x in (r.potential_loss_cents, r.executed_loss_cents)):
                raise ValueError('A recorded loss exceeds the declared cap')
        text = self.model_dump_json()
        if re.search(r'(?i)(sk-ant-[a-z0-9_-]{8,}|bearer\s+[a-z0-9._-]{12,}|-----BEGIN.*PRIVATE KEY)', text):
            raise ValueError('Remove credentials before importing traces')
        return self


def directory():
    root = Path(os.getenv('DATABASE_PATH', 'data/riskgraph.sqlite3')).parent / 'private-evidence'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def save(batch):
    batch_id = uuid4().hex
    path = directory() / (batch_id + '.json')
    with path.open('x') as f:
        os.chmod(path, 0o600)
        json.dump(batch.model_dump(), f, indent=2)
    return {'id': batch_id, 'summary': summarize(batch.model_dump())}


def read(batch_id):
    if not re.fullmatch(r'[0-9a-f]{32}', batch_id): raise ValueError('Unknown evidence batch')
    path = directory() / (batch_id + '.json')
    if not path.is_file(): raise ValueError('Unknown evidence batch')
    return EvidenceBatch.model_validate_json(path.read_text()).model_dump()


def summarize(batch):
    rows = batch['episodes']
    known = [r for r in rows if r['reviewed'] and r['potential_loss_cents'] is not None]
    return {'source': batch['source'], 'system_version': batch['system_version'], 'reference_configuration': batch['reference_configuration'],
            'episodes': len(rows), 'reviewed_known_potential_loss': len(known), 'unresolved_potential_loss': len(rows) - len(known),
            'observed_harmful': sum(r['potential_loss_cents'] > 0 for r in known),
            'outside_test_catalogue': sum(r['scenario'] not in FAMILIES for r in rows),
            'counts_are_episodes_not_agent_events': True}


class ProjectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    configuration: str = Field(min_length=1, max_length=120)
    batch_id: Optional[str] = Field(default=None, max_length=32)
    observed_share: float = Field(default=0., ge=0, le=1)
    unmodeled_mass: float = Field(default=0., ge=0, le=1)
    threshold_usd: float = Field(default=0., ge=0, le=10000000)
    weights: dict[str, float] = Field(default_factory=lambda: {f: 1 / len(FAMILIES) for f in FAMILIES})

    @model_validator(mode='after')
    def valid_mix(self):
        if set(self.weights) != set(FAMILIES) or any(not np.isfinite(v) or v < 0 for v in self.weights.values()) or abs(sum(self.weights.values()) - 1) > 1e-8:
            raise ValueError('Eight nonnegative scenario weights must sum to one')
        return self


def project(study, request, batch=None):
    if study.get('status') != 'complete' or 'analysis' not in study:
        raise ValueError('The fixed simulation batch must complete before projection')
    model, memory, critic = request.configuration.split('|')
    if request.configuration not in study['analysis']['arms']: raise ValueError('Unknown simulation reference configuration')
    if batch is not None:
        if batch['source'] != 'observed': raise ValueError('Only observed episodes may enter the observed evidence lane; illustration and simulation remain separate')
        if batch['reference_configuration'] != request.configuration: raise ValueError('The imported simulation reference does not match the selected configuration')
        if request.observed_share > 0 and request.unmodeled_mass == 0 and any(r['scenario'] not in FAMILIES for r in batch['episodes']):
            raise ValueError('Observed failures outside the catalogue require an explicit nonzero unmodeled-mass assumption')
    rows = [r for r in study['cells'] if r['workflow'] == 'grounded' and r['model'] == model and r['memory_mode'] == memory]
    by_id = {c['id']: c['family'] for c in study['cases']}; stage = 'corrected_outcome' if critic == '1' else 'initial_outcome'
    rng = np.random.default_rng(20261024191); lower = np.zeros(12000); upper = np.zeros(12000)
    empirical_lo = empirical_hi = mean_lo = mean_hi = 0.; sources = []; prior_only = []
    threshold = request.threshold_usd * 100
    for source, share in (('simulation', 1 - request.observed_share), ('observed', request.observed_share)):
        counts = {}
        for family, weight in request.weights.items():
            if source == 'simulation':
                episodes = [r[stage] for r in rows if by_id[r['case_id']] == family]
                values = [o['proposed_loss_cents'] if o['resolved'] else None for o in episodes]
            else:
                episodes = [r for r in (batch or {}).get('episodes', []) if r['scenario'] == family]
                values = [r['potential_loss_cents'] if r['reviewed'] else None for r in episodes]
            n = len(values); k = sum(v is not None and v > threshold for v in values); unknown = sum(v is None for v in values)
            counts[family] = {'episodes': n, 'above_threshold': k, 'unresolved': unknown}
            scale = share * weight
            if not n:
                upper += scale; empirical_hi += scale; mean_hi += scale
                if scale: prior_only.append(source + ':' + family)
                continue
            # Bound unresolved labels rather than treating missing financial outcomes as zero.
            lo_draw = rng.beta(k + .5, n - k + .5, 12000)
            hi_draw = lo_draw if not unknown else rng.beta(k + unknown + .5, n - k - unknown + .5, 12000)
            lower += scale * lo_draw; upper += scale * hi_draw
            mean_lo += scale * (k + .5) / (n + 1); mean_hi += scale * (k + unknown + .5) / (n + 1)
            empirical_lo += scale * k / n; empirical_hi += scale * (k + unknown) / n
        sources.append({'source': source, 'assumed_share': share, 'counts': counts})
    epsilon = request.unmodeled_mass
    lo = float(np.quantile(lower, .025)) * (1 - epsilon)
    hi = float(np.quantile(upper, .975)) * (1 - epsilon) + epsilon
    return {'formula': 'P(L > t) = (1-epsilon) sum_s w_s [(1-rho) p_sim,s + rho p_obs,s] + epsilon q_unseen, with q_unseen in [0,1]',
            'assumptions': request.model_dump(), 'sources': sources, 'missing_source_strata': prior_only,
            'model_based95_range': [lo, hi], 'posterior_mean_sensitivity': [mean_lo * (1 - epsilon), mean_hi * (1 - epsilon) + epsilon],
            'empirical_missing_and_unmodeled_range': [empirical_lo * (1 - epsilon), empirical_hi * (1 - epsilon) + epsilon],
            'outside_catalogue_observed_episodes': sum(r['scenario'] not in FAMILIES for r in (batch or {}).get('episodes', [])),
            'scope': 'A source-transfer sensitivity projection, not a pooled estimate of production incidence. Scenario weights, observed share rho, and unmodeled mass epsilon are explicit assumptions, not learned from discovery. Reviewed labels are operator attestations, not automatically verified external facts. Each source retains its own counts and Jeffreys working model. Unobserved source/scenario components retain the full [0,1] range, not a fabricated point estimate. Unresolved labels are bounded at both extremes. The displayed range is a marginal model-based envelope, not a frequentist confidence guarantee; changing the assumptions changes the target. Episodes must be independent for the working sampling model. No trace content is sent to a model by importing or calculating this projection.'}
