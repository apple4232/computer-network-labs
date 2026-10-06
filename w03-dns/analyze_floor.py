"""Independent TTL interval lower bound; does not call YourCache."""
from collections import Counter
import json
from pathlib import Path
from bench import FIXTURE, workload


def analyze():
    expires, stored = {}, {}
    floor, baseline, stale = Counter(), Counter(), Counter()
    for now, name in workload():
        if now >= expires.get(name, float('-inf')):
            floor[name] += 1
            expires[name] = now + FIXTURE[name][1]
        if name not in stored or now >= stored[name] + 60:
            baseline[name] += 1
            stored[name] = now
        elif now > stored[name] + FIXTURE[name][1]:
            stale[name] += 1
    return {"minimum_upstream": sum(floor.values()),
            "per_name": {name: {"ttl": FIXTURE[name][1], "floor": floor[name],
                                "baseline_calls": baseline[name],
                                "baseline_stale": stale[name]}
                         for name in FIXTURE}}


if __name__ == '__main__':
    result = analyze()
    out = Path(__file__).parent / 'out'
    out.mkdir(exist_ok=True)
    (out / 'floor.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
