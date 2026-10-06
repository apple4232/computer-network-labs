#!/usr/bin/env python3
"""Week 3 · Task 1 — Build your own iterative resolver.

Textbook §2.4.2 - §2.4.3.

`dig +trace` walks root -> TLD -> authoritative for you. In this task you do
that walk yourself: start at a root server, read the delegation it returns,
ask the next server, and keep going until somebody answers authoritatively.

You may shell out to `dig` for the transport, or use a DNS library
(`dnspython` is in the container). Either is fine - what matters is that
*you* follow the delegations rather than letting a tool do it.

    python3 task1_resolve.py www.korea.ac.kr
    python3 task1_resolve.py --verify        # check yourself against dig

Pass condition
--------------
`--verify` resolves five names with your resolver and with `dig`, and the
addresses must agree. A name behind a CDN may legitimately return a different
address each time; the harness compares the *set of authoritative nameservers*
you ended at for those, not the address.
"""
import argparse, subprocess, sys
import json
import shutil
from pathlib import Path
import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdatatype
import dns.resolver

# Root servers. Everything starts here; there is no earlier step.
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
]

# (name, kind).  "stable" names must match dig exactly.  "cdn" names are served
# from many replicas and may legitimately give you a different address than dig
# got a second earlier - for those we only require that you reached an answer.
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class Resolver:
    """Your iterative resolver.

    The whole point is that you never ask a server to recurse for you.
    You ask one server, it says "not mine, ask over there", and you go there.

    Suggested shape - but it is yours to design:

        resolve(name) -> (address, path)
            address : the A record you ended up with, as a string
            path    : the servers you asked, in order, so you can show your work

    Things you will hit, in roughly this order:

    1.  A delegation gives you NS *names*, sometimes with glue A records and
        sometimes without. No glue means you have to resolve that nameserver's
        name first - which is another walk. Decide what you do there.
    2.  A server may not answer. Try the next one rather than giving up.
    3.  CNAMEs. The answer you get back may be a different name than the one
        you asked for, and you have to start again with that name.
    4.  Loops. Cap your depth.

    If you shell out to dig, the flag you want is `+norecurse`, so that the
    server you ask replies with a delegation instead of doing the work:

        dig @198.41.0.4 www.korea.ac.kr +norecurse
    """

    def __init__(self, timeout=2.0, max_depth=24, max_queries=160, query=None, source_port=0):
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_queries = max_queries
        self.query = query or self._query
        self.events = []
        self.source_port = source_port

    def _query(self, name, server):
        question = dns.message.make_query(name, "A")
        question.flags &= ~dns.flags.RD
        response = dns.query.udp(question, server, timeout=self.timeout,
                                 ignore_unexpected=True, source_port=self.source_port)
        if response.flags & dns.flags.TC:
            response = dns.query.tcp(question, server, timeout=self.timeout)
        return response

    def resolve(self, name):
        self.events = []
        path = []
        address = self._walk(dns.name.from_text(name), path, (), 0)
        return address, path

    def _walk(self, name, path, active, depth):
        if len(path) >= self.max_queries:
            raise RuntimeError('global DNS query limit reached')
        if depth >= self.max_depth or name in active:
            raise RuntimeError(f"DNS dependency/CNAME loop or depth limit: {name}")
        active = (*active, name)
        servers = list(ROOT_SERVERS)
        zone = dns.name.root
        seen = set()
        for _ in range(self.max_depth):
            next_servers = []
            for server in servers:
                if isinstance(server, dns.name.Name):
                    try:
                        server = self._walk(server, path, active, depth + 1)
                    except (RuntimeError, dns.exception.DNSException, OSError):
                        continue
                state = (name.to_text(), server)
                if state in seen:
                    continue
                seen.add(state)
                if len(path) >= self.max_queries:
                    raise RuntimeError("global DNS query limit reached")
                path.append(server)
                event = {"name": name.to_text(), "server": server}
                self.events.append(event)
                try:
                    reply = self.query(name, server)
                except (dns.exception.DNSException, OSError) as exc:
                    event["error"] = str(exc)
                    continue
                event.update(rcode=dns.rcode.to_text(reply.rcode()),
                             authoritative=bool(reply.flags & dns.flags.AA),
                             answer=[str(rr) for rr in reply.answer],
                             authority=[str(rr) for rr in reply.authority],
                             additional=[str(rr) for rr in reply.additional])
                if reply.rcode() == dns.rcode.NXDOMAIN and reply.flags & dns.flags.AA:
                    raise RuntimeError(f"authoritative NXDOMAIN: {name}")
                if reply.rcode() != dns.rcode.NOERROR:
                    continue
                if reply.flags & dns.flags.AA:
                    for rrset in reply.answer:
                        if rrset.name == name and rrset.rdtype == dns.rdatatype.A:
                            return rrset[0].address
                    for rrset in reply.answer:
                        if rrset.name == name and rrset.rdtype == dns.rdatatype.CNAME:
                            return self._walk(rrset[0].target, path, active, depth + 1)
                    if any(rr.rdtype == dns.rdatatype.SOA for rr in reply.authority):
                        raise RuntimeError(f"authoritative NODATA: {name}")
                referrals = [rr for rr in reply.authority
                             if rr.rdtype == dns.rdatatype.NS and name.is_subdomain(rr.name)]
                if not referrals:
                    continue
                delegation = max(referrals, key=lambda rr: len(rr.name.labels))
                ns_names = [rr.target for rr in delegation]
                # Trust glue only for the selected NS names within the responding
                # parent zone. Root glue may cross TLDs (e.g. .com NS in .net).
                glued = set()
                for rr in reply.additional:
                    if (rr.rdtype == dns.rdatatype.A and rr.name in ns_names
                            and rr.name.is_subdomain(zone)):
                        next_servers.extend(record.address for record in rr)
                        glued.add(rr.name)
                # Lazy no-glue candidates also provide fallback if supplied glue is dead.
                next_servers.extend(ns for ns in ns_names if ns not in glued)
                if next_servers:
                    zone = delegation.name
                    break
            if not next_servers:
                raise RuntimeError(f"no responding nameserver or usable delegation for {name}")
            servers = list(dict.fromkeys(next_servers))
        raise RuntimeError(f"delegation depth limit: {name}")


# ------------------------------------------------------------------- harness
def dig_answer(name):
    """What the system resolver says, for comparison."""
    if not shutil.which('dig'):
        return sorted(record.address for record in dns.resolver.resolve(name, 'A', lifetime=8))
    out = subprocess.run(["dig", "+short", name, "A"],
                         capture_output=True, text=True).stdout
    return [l for l in out.split() if l and l[0].isdigit()]


def verify():
    if not shutil.which('dig'):
        print('dig unavailable: independent reference = dnspython system recursive resolver')
    r, failures = Resolver(), 0
    for name, kind in VERIFY_NAMES:
        try:
            addr, path = r.resolve(name)
        except NotImplementedError:
            print("Nothing implemented yet - write Resolver.resolve first.")
            return 1
        except Exception as e:
            print(f"  FAIL  {name:<22} your resolver raised {e!r}")
            failures += 1
            continue
        expected = dig_answer(name)
        if addr in expected:
            note = ""
        elif kind == "cdn":
            note = "  <- differs, but this name is CDN-hosted. Explain it."
        else:
            note = "  <- should have matched"
            failures += 1
        print(f"  {'FAIL' if note.endswith('matched') else 'ok  '}  {name:<22} "
              f"you={addr:<16} reference={','.join(expected) or '-'}   "
              f"hops={len(path)}{note}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", nargs="?", default="www.korea.ac.kr")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--log", help="save every query/referral/error as JSON")
    p.add_argument("--source-port", type=int, default=0, help="optional port for narrowly filtered captures")
    a = p.parse_args()

    if a.verify:
        sys.exit(verify())

    resolver = Resolver(source_port=a.source_port)
    try:
        addr, path = resolver.resolve(a.name)
    finally:
        if a.log:
            Path(a.log).parent.mkdir(parents=True, exist_ok=True)
            with open(a.log, "w", encoding="utf-8") as f:
                json.dump(resolver.events, f, ensure_ascii=False, indent=2)
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {a.name} -> {addr}")


if __name__ == "__main__":
    main()
