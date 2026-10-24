"""Fresh, regression-enriched cases from the frozen hard generator."""
from .memory_cases import generate as original_generate
from .hardcases import digest

VERSION = 'memory-regression-followup-v4'
SEED = 2026102441
FAMILIES = ('elapsed_time', 'nested_reversals', 'approval_boundary')


def generate(per_family=16):
    if type(per_family) is not int or not 4 <= per_family <= 100:
        raise ValueError('Unsupported prespecified per-family sample size')
    cases = [c for c in original_generate(SEED, per_family) if c['family'] in FAMILIES]
    for c in cases:
        c['id'] = c['id'].replace('v3-', 'v4-', 1)
        c['truth']['id'] = c['id']
    assert len(cases) == per_family * len(FAMILIES)
    return cases
