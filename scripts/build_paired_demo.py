"""Reproduce the frozen fixture without any external API calls."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.paired_demo import build_bundle, BUNDLE

if __name__ == '__main__':
    bundle = build_bundle()
    BUNDLE.write_text(json.dumps(bundle, indent=2) + '\n')
    print('Saved 60 held-out + 12 development synthetic cases, 3 curated examples, and 3 separate archived real-model cases.')
    print('Held-out evidence SHA256:', bundle['evidence_digest'])
