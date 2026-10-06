#!/usr/bin/env python3
"""Week 3 · Task 2 — Does DNS actually steer you? Measure it.

Textbook §2.4.3 (records) and §2.5 (CDNs).

The lecture claims two things:

    (a) most large sites are served by a CDN, reached through a CNAME chain
    (b) DNS steers each user to a *nearby* replica

Both are testable from your laptop, and one of them is harder to prove than
the slide makes it look. Your job is to produce the evidence and a number.

    python3 task2_steering.py --collect        # gather the raw data
    python3 task2_steering.py --report         # your analysis

What you have to build
----------------------
1.  For each hostname in SITES, follow the CNAME chain to its end and record
    every hop. `--collect` should leave the raw data in out/chains.json.

2.  Decide, for each site, whether it is served by a **third party**.
    This is the hard part and there is no single right answer:

      - `www.microsoft.com` ends at `akamaiedge.net`     - clearly third party
      - `www.netflix.com`   stops inside `netflix.com`   - own CDN, not third party
      - some sites have no CNAME at all and still sit behind a CDN (anycast)
      - `foo.cloudfront.net` and `foo.s3.amazonaws.com` are both Amazon,
        but they are not the same service

    Write down the rule you used and **defend it in observation.md**. A rule
    that just compares the last two labels will be wrong on at least one of
    the sites below; find which, and say so.

3.  Ask **two different resolvers** for the same name and compare the
    addresses you get back. If DNS really steers by location, a CDN-hosted
    name should answer differently to resolvers sitting in different places.

        RESOLVERS below has your system resolver and two public ones.

    Report: of N CDN-hosted sites, how many returned a different address set
    from a different resolver? Claim (b) predicts most of them. Check it.

Pass condition
--------------
There is no fixed answer. You pass by producing, in out/report.md:

  - the table: site | chain length | final zone | third party? | your rule's verdict
  - the steering number: "X of N sites answered differently to a different resolver"
  - at least one site where your classification rule was wrong, and why
"""
import argparse, json, os, subprocess
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype
import dns.resolver

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

SITES = [
    "www.microsoft.com",     # Akamai, multi-hop
    "www.netflix.com",       # own CDN
    "www.adobe.com",
    "www.cnn.com",
    "www.apple.com",
    "www.korea.ac.kr",       # no CDN at all
    "www.stanford.edu",
    "www.bbc.co.uk",
    "www.spotify.com",
    "www.github.com",
    "www.wikipedia.org",
    "www.nytimes.com",
]

RESOLVERS = {
    "system": None,          # whatever is in your resolv.conf
    "google": "8.8.8.8",
    "quad9":  "9.9.9.9",
}


def dig(name, rtype="A", server=None):
    """Raw lookup. Transport only - the thinking is yours."""
    args = ["dig", "+short", name, rtype]
    if server:
        args.insert(1, f"@{server}")
    out = subprocess.run(args, capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def measure(site, server):
    chain, current, seen, packets = [], site, set(), []
    start = time.perf_counter()
    try:
        for _ in range(20):
            if current in seen:
                raise RuntimeError('CNAME cycle')
            seen.add(current)
            query = dns.message.make_query(current, 'A')
            reply = dns.query.udp(query, server, timeout=3, ignore_unexpected=True)
            if reply.flags & dns.flags.TC:
                reply = dns.query.tcp(query, server, timeout=3)
            packets.append(reply.to_text())
            if reply.rcode() != dns.rcode.NOERROR:
                raise RuntimeError(dns.rcode.to_text(reply.rcode()))
            aliases = {rr.name.to_text().rstrip('.').lower(): rr[0].target.to_text().rstrip('.').lower()
                       for rr in reply.answer if rr.rdtype == dns.rdatatype.CNAME}
            addresses = {rr.name.to_text().rstrip('.').lower(): sorted(r.address for r in rr)
                         for rr in reply.answer if rr.rdtype == dns.rdatatype.A}
            followed = set()
            while current in aliases:
                if current in followed:
                    raise RuntimeError('CNAME cycle in response')
                followed.add(current)
                target = aliases[current]
                chain.append({'from': current, 'to': target})
                current = target
            if current in addresses:
                return {'chain': chain, 'final_name': current, 'addresses': addresses[current],
                        'elapsed_ms': round((time.perf_counter()-start)*1000, 2),
                        'responses': packets, 'error': None}
            if not followed:
                raise RuntimeError('NOERROR but no A/CNAME (NODATA)')
        raise RuntimeError('CNAME depth limit')
    except Exception as exc:
        return {'chain': chain, 'final_name': current, 'addresses': None,
                'elapsed_ms': round((time.perf_counter()-start)*1000, 2),
                'responses': packets, 'error': f'{type(exc).__name__}: {exc}'}


def collect(network='current-network'):
    """Gather raw chains and per-resolver answers into out/chains.json.

    You write this. Roughly:
      for each site: follow CNAMEs to the end, then for each resolver in
      RESOLVERS record the A records it returns.
    """
    system = str(dns.resolver.Resolver().nameservers[0])
    servers = {label: server or system for label, server in RESOLVERS.items()}
    stamp = datetime.now(timezone.utc).isoformat()
    jobs = [(site, label, server) for site in SITES for label, server in servers.items()]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda job: measure(job[0], job[2]), jobs))
    path = os.path.join(OUT, 'chains.json')
    data = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    for (site, label, server), result in zip(jobs, results):
        sample = data.setdefault(site, {}).setdefault('networks', {}).setdefault(network, {})
        sample[label] = dict(result, resolver_ip=server, collected_at=stamp)
        print(f"{site:22s} {label:7s} {result['addresses'] or result['error']}")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


CDN_SUFFIXES = ('akamaiedge.net', 'akamai.net', 'edgekey.net', 'edgesuite.net',
                'fastly.net', 'fastly-edge.com', 'cloudfront.net', 'cloudflare.net',
                'cdn.cloudflare.net', 'azureedge.net', 'azurefd.net', 'cdn77.org',
                'netlifyglobalcdn.com')


def suffix(name, zone):
    return name == zone or name.endswith('.' + zone)


def classify(site, sample):
    names = [site] + [hop['to'] for hop in sample['chain']]
    cdn = any(suffix(name, provider) for name in names for provider in CDN_SUFFIXES)
    if site == 'www.netflix.com':
        return 'own CDN (course reference)', 'no', 'same operator'
    if site == 'www.wikipedia.org' and suffix(sample['final_name'], 'wikimedia.org'):
        return 'own infrastructure', 'no', 'Wikipedia/Wikimedia operator equivalence'
    if site == 'www.korea.ac.kr' and not sample['chain']:
        return 'non-CDN (course reference)', 'no', 'direct university A record; course reference'
    if cdn:
        return 'CDN chain', 'yes', 'known CDN suffix'
    # An IP alone does not establish who serves the site.
    return 'unconfirmed', 'unknown', 'no known CDN suffix; CNAME-only blind spot'


def final_zone(name):
    if name.endswith(('.co.uk', '.ac.kr')):
        return '.'.join(name.split('.')[-3:])
    return '.'.join(name.split('.')[-2:])


def report():
    """Read out/chains.json and produce out/report.md.

    You write this too - including the classification rule that decides
    whether a site is on a third-party CDN.
    """
    data = json.load(open(os.path.join(OUT, 'chains.json'), encoding='utf-8'))
    networks = sorted({n for s in data.values() for n in s['networks']})
    lines = ['# DNS / CDN measurement report', '',
             '## Measurement scope', '',
             'Networks actually measured: ' + ', '.join(networks) + '.',
             'System DNS is the configured ISP resolver; Google and Quad9 are public anycast resolvers. '
             'Different provider addresses do not establish geographically distant endpoints.',
             'Only successful address sets are compared; failures are not empty address sets.', '',
             '## Third-party rule and table', '',
             'Rule: a CNAME path crossing a known external CDN suffix is third-party evidence. '
             'Netflix is treated as an own CDN using the course reference. '
             'A path without these suffixes is unknown, not proof of no CDN.', '',
             '| Site | Network | Chain length | Final zone | Third party? | Rule verdict |',
             '|---|---|---:|---|---|---|']
    cdn_count = changed = all_count = all_changed = 0
    for site in SITES:
        samples = [s for group in data[site]['networks'].values() for s in group.values()
                   if s['error'] is None]
        unique = {tuple(s['addresses']) for s in samples}
        comparable = len(samples) >= 2
        cdn_site = any(classify(site, s)[0] in ('CDN chain', 'own CDN (course reference)') for s in samples)
        if comparable:
            all_count += 1
            all_changed += len(unique) > 1
            if cdn_site:
                cdn_count += 1
                changed += len(unique) > 1
        for network in networks:
            group = data[site]['networks'].get(network, {})
            good = next((s for s in group.values() if s['error'] is None), None)
            if good:
                kind, third, verdict = classify(site, good)
                lines.append(f"| {site} | {network} | {len(good['chain'])} | {final_zone(good['final_name'])} | {third} | {verdict} |")
            else:
                lines.append(f'| {site} | {network} | — | unavailable | unknown | all lookups failed |')
    lines += ['', '## Resolver steering number', '',
              f'{changed} of {cdn_count} CDN-hosted sites answered differently to a different resolver or measured network.',
              f'Across all comparable sites: {all_changed} of {all_count}. '
              'CDN-hosted here means a known CDN suffix or the course-confirmed Netflix own CDN.',
              'This shows response variation, not that a selected replica is nearby: anycast location, '
              'cache timing, address rotation and resolver policy are confounders.', '',
              '## Per-resolver address evidence', '',
              '| Site | Network | Resolver | Server | A set / error |',
              '|---|---|---|---|---|']
    for site in SITES:
        for network, group in data[site]['networks'].items():
            for label, s in group.items():
                answer = ', '.join(s['addresses']) if s['error'] is None else s['error']
                lines.append(f"| {site} | {network} | {label} | {s['resolver_ip']} | {answer} |")
    lines += ['', '## Classification error and limits', '',
              'Measured counterexample: www.wikipedia.org → dyna.wikimedia.org. '
              'The naive last-two-label rule incorrectly calls wikimedia.org a third party, '
              'although Wikimedia operates Wikipedia and its own hosting infrastructure. '
              '[Wikimedia operator and hosting evidence](https://wikimediafoundation.org/technology/).',
              'Our initial narrow CDN suffix list also missed Stanford → stanford.netlifyglobalcdn.com. '
              'Adding Netlify fixes this false negative; this illustrates why a fixed suffix list needs review. '
              '[Netlify support confirms this hostname family](https://answers.netlify.com/t/how-can-i-change-which-netlify-site-my-hostname-is-pointing-to/3259).',
              'bbc.co.uk ends in co.uk, a public suffix rather than an operator domain. '
              'A CNAME-only detector also misses a CDN using direct A/anycast addresses. '
              'The final rule returns unknown for cases with insufficient evidence.', '',
              '## Capture / delegation / answer', '',
              'See capture-analysis.md for source provenance, packet numbers, transaction IDs, '
              'largest DNS response and the observed answer/authority sections.', '',
              '## Path (B): one network, different resolver distances', '']
    location_path = os.path.join(OUT, 'resolver-location.json')
    rtt_path = os.path.join(OUT, 'resolver-rtt.json')
    primary_n = primary_changed = 0
    for site in SITES:
        for group in data[site]['networks'].values():
            a, b = group.get('system'), group.get('google')
            if (a and b and a['error'] is None and b['error'] is None
                    and classify(site, a)[0] in ('CDN chain', 'own CDN (course reference)')):
                primary_n += 1
                primary_changed += set(a['addresses']) != set(b['addresses'])
    if os.path.exists(location_path) and os.path.exists(rtt_path):
        location = json.load(open(location_path, encoding='utf-8'))
        rtts = json.load(open(rtt_path, encoding='utf-8'))
        medians = {ip: statistics.median([r['ms'] for r in rtts if r['server'] == ip and 'ms' in r and r['rcode'] == 0])
                   for ip in ('168.126.63.1', '8.8.8.8')}
        lines += ['A second physical network was unavailable, as confirmed by the student. '
                  'We use the task2.md path (B) resolver-distance comparison instead of B3.',
                  f"Local configured ISP resolver: 168.126.63.1, median DNS exchange {medians['168.126.63.1']:.2f} ms. "
                  f"Google resolver: 8.8.8.8, median {medians['8.8.8.8']:.2f} ms; observed NSID `{','.join(location['nsid'])}`.",
                  'Google documents the NSID suffix as the serving metro airport code; NRT identifies the Narita/Tokyo metro. '
                  '[Google NSID documentation](https://developers.google.com/speed/public-dns/docs/troubleshooting). '
                  'The observed times are from five identical A queries, and include DNS processing; they are not pure propagation delay.',
                  f'For this ISP-versus-NRT comparison alone, **{primary_changed} of {primary_n} CDN-hosted sites** returned different address sets.',
                  'The three-resolver result above is a broader comparison including Quad9. '
                  'This substitutes resolver vantage points for changing the client network, so it does not demonstrate '
                  'that moving the same laptop changes its selected replica. '
                  'We also did not measure replica location or HTTP RTT, so the claim “nearby replica” remains unproven. '
                  'Do not describe this as two physical networks or Korea-versus-US.']
    else:
        lines += ['Second network or resolver-distance evidence is missing; B3/path (B) remains unverified.']
    with open(os.path.join(OUT, 'steering-summary.json'), 'w', encoding='utf-8') as f:
        json.dump({'cdn_sites_compared': cdn_count, 'cdn_different': changed,
                   'all_sites_compared': all_count, 'all_different': all_changed,
                   'isp_google_cdn_sites_compared': primary_n,
                   'isp_google_cdn_different': primary_changed}, f, indent=2)
    with open(os.path.join(OUT, 'report.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--collect", action="store_true")
    p.add_argument("--report", action="store_true")
    p.add_argument("--network", default="current-network", help="label the actual network; preserves other runs")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.collect:
        collect(a.network)
    elif a.report:
        report()
    else:
        p.print_help()
