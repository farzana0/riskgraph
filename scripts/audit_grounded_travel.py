"""Descriptive control/revision mistakes, without inferring private model causes."""
import json
from collections import Counter
from pathlib import Path


def audit(study):
    mistakes = []; counts = {}
    for row in study['cells']:
        for stage in ('initial', 'corrected'):
            out, call = row[stage + '_outcome'], row[stage]
            if not out['task_failure']: continue
            kind = 'unresolved' if not out['resolved'] else 'harmful_proposal' if out['proposed_loss_cents'] else 'unnecessary_escalation'
            mistakes.append({'case_id': row['case_id'], 'workflow': row['workflow'], 'model': row['model'],
                             'memory_mode': row['memory_mode'], 'stage': stage, 'classification': kind,
                             'proposal': call.get('proposal'), 'status': call['status'], 'stop_reason': call.get('stop_reason'),
                             'response_id': call.get('response_id'), 'gate_rules': (out.get('gate') or {}).get('rules'),
                             'potential_loss_cents': out['proposed_loss_cents']})
    for w in ('legacy', 'grounded'):
        counts[w] = dict(Counter(r['classification'] for r in mistakes if r['workflow'] == w))
    calls = [row[stage] for row in study['cells'] for stage in ('initial', 'corrected')]
    return {'source': study['schema_version'], 'trips': 32, 'configurations': 16, 'classifications': counts,
            'call_statuses': dict(Counter(c['status'] for c in calls)),
            'invalid_response_stop_reasons': dict(Counter(c.get('stop_reason') for c in calls if c['status'] == 'invalid_response')),
            'mistakes': mistakes,
            'observations': ['Original-control explanations repeat incorrect signed-time comparisons and sometimes describe an eligible offer while the saved action escalates.',
                             'Original-control harmful proposals include arithmetic, deadline and connection violations.',
                             'No adjudicated revised-workflow proposal is harmful or unnecessarily escalates on this fixed batch. Two initial Haiku/no-memory outputs hit the shared cap; their unavailable critic outcomes remain unresolved.',
                             'The revised Sonnet arms have no observed task errors here. This is not a general model ranking or a zero-risk claim.'],
            'limits': 'These are descriptive counts across dependent configurations of 32 trips, not independent incident counts. Eight schema-rejected end_turn responses have no archived valid proposal; their precise validation cause is not inferred. Seven requests hit max_tokens. Skipped reviews remain unavailable, never fabricated. The revised package changes arithmetic support and prompting; its effect cannot be attributed solely to SurrealDB. Marginal credible intervals and conservative simultaneous bounds answer different questions.'}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    out = audit(json.loads((root / 'docs/examples/travel-v3.json').read_text()))
    (root / 'docs/examples/travel-v3-error-audit.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'mistakes'}, indent=2))
