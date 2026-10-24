"""Descriptive audit of saved decisions; hypotheses about causes stay explicit."""
import json
import statistics
from collections import Counter
from pathlib import Path


def audit(path):
    study = json.loads(path.read_text()); mistakes = []; summaries = {}
    for row in study['cells']:
        for stage in ('initial', 'corrected'):
            out = row[stage + '_outcome']
            if out['task_failure']:
                mistakes.append({'case_id': row['case_id'], 'model': row['model'], 'memory_mode': row['memory_mode'],
                                 'stage': stage, 'classification': 'unsafe_booking' if (out['proposed_loss_cents'] or 0) > 0 else 'unnecessary_escalation' if row[stage].get('proposal', {}).get('action') == 'escalate' else 'unresolved',
                                 'gate_rules': out['gate']['rules'] if out['gate'] else [], 'proposed_loss_cents': out['proposed_loss_cents'],
                                 'proposal': row[stage].get('proposal'), 'response_id': row[stage].get('response_id')})
    for m in study['design']['models']:
        calls = [r['initial'] for r in study['cells'] if r['model'] == m]
        summaries[m] = {'initial_requests': len(calls), 'actions': dict(Counter(r['proposal']['action'] for r in calls)),
                        'mean_output_tokens': statistics.mean(r['usage']['output_tokens'] for r in calls),
                        'max_output_tokens': max(r['usage']['output_tokens'] for r in calls), 'stop_reasons': dict(Counter(r['stop_reason'] for r in calls))}
    return {'source': 'travel-factorial-v2', 'mistake_count': len(mistakes), 'classifications': dict(Counter(r['classification'] for r in mistakes)),
            'models': summaries, 'mistakes': mistakes,
            'observed_mechanisms': ['Unnecessary escalations despite a current eligible offer.', 'Incorrect signed time differences and comparisons at exact-second boundaries.', 'Short explanations sometimes describe a passing offer while the saved action escalates, or admit lateness while the action books.'],
            'hypotheses_not_causal_findings': ['Action is serialized before the short reason in the common schema; early commitment may prevent later corrections from changing it.', 'Generic corrective-review instructions may encourage unsupported overturns.', 'Long procedural context can add distraction; this was not isolated by a context-length control.'],
            'limits': 'One small synthetic challenge set with one generation per configuration. All outputs ended normally and no request reached the 1536-token cap. Output token counts include adaptive thinking; they do not reveal private reasoning. The findings do not establish a general model ranking or a causal explanation of internal model behavior.'}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    result = audit(root / 'docs/examples/travel-factorial.json')
    (root / 'docs/examples/travel-error-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'classifications': result['classifications'], 'models': result['models']}, indent=2))
