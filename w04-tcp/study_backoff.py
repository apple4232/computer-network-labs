"""Compare loss responses through the unchanged benchmark interface."""
import json
from pathlib import Path
from bench import simulate
from task3_congestion import YourControl


def main():
    results = []
    for beta in (0.5, 0.6, 0.65, 0.7, 0.75, 0.8):
        windows = []

        class Trial(YourControl):
            def __init__(self):
                super().__init__()
                self.backoff = beta

            def on_ack(self):
                super().on_ack()
                windows.append(self.window)

        result = simulate(Trial)
        result.update(backoff=beta, last_1000_acks_window_min=min(windows[-1000:]),
                      last_1000_acks_window_max=max(windows[-1000:]))
        results.append(result)
    output = json.dumps(results, indent=2)
    (Path(__file__).parent / 'out' / 'backoff-study.json').write_text(output, encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
