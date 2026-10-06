# Cache correctness and lower bound

The unmodified benchmark replays 1,000 queries over 3,600 seconds.

| Cache | Upstream | Hit rate | Stale | Simulated time |
|---|---:|---:|---:|---:|
| Baseline | 325 | 67.5% | 266 | 6.5 s |
| YourCache | 275 | 72.5% | 0 | 5.5 s |

The 50 fewer upstream calls are a 15.38% reduction. Correctness is improved at the same time.

The baseline discards the authoritative TTL and uses a fixed 60-second lifetime. This has two consequences: records with TTL below 60 seconds become stale, while long-lived records are discarded prematurely and trigger unnecessary upstream calls. Its linear list scan adds a separate local performance cost. YourCache uses a dictionary and the expiry returned by each upstream response. At `now == expires_at`, it refreshes; a zero TTL never produces a cache hit.

## Independent floor calculation

`analyze_floor.py` groups the actual benchmark workload by name, without calling YourCache. For each name it begins a freshness interval at the first demand and begins the next interval at the first demand at or after expiry. The per-name counts in `floor.json` are:

| Name | TTL (s) | Mandatory intervals | Baseline upstream | Baseline stale |
|---|---:|---:|---:|---:|
| www.microsoft.com | 20 | 118 | 52 | 189 |
| www.cnn.com | 30 | 76 | 47 | 77 |
| www.netflix.com | 60 | 37 | 37 | 0 |
| www.spotify.com | 120 | 23 | 38 | 0 |
| www.github.com | 300 | 11 | 27 | 0 |
| www.wikipedia.org | 600 | 6 | 31 | 0 |
| www.korea.ac.kr | 3600 | 1 | 25 | 0 |
| www.stanford.edu | 3600 | 1 | 27 | 0 |
| dns.google | 86400 | 1 | 21 | 0 |
| a.root-servers.net | 86400 | 1 | 20 | 0 |
| **Total** | | **275** | **325** | **266** |

At the first uncovered demand, any correct cache must already have fetched a fresh answer, or fetch one then. Fetching earlier would end that answer's fixed TTL earlier; fetching later cannot answer the current demand. Fetching exactly at this first uncovered demand therefore covers at least as far into the future as any alternative fetch that covers it. Repeating this argument proves that these greedy intervals minimize the number of fetches. Different names require separate upstream lookups in the provided interface, so their lower bounds add to **275**. Prefetching cannot lower this number: it shifts a fetch earlier and cannot extend its lifetime.

The fixture's constant IP strings do not permit a correct DNS cache to ignore expiry: a real authoritative answer can change after its TTL. The benchmark's stale check uses `t > expiry`; our cache uses the stricter correct boundary `t >= expiry`, tested separately. No supplied harness or fixture was modified.
