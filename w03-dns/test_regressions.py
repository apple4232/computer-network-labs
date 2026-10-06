"""Protocol edge cases and TTL boundary checks; no live network required."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import dns.exception
import dns.flags
import dns.message
import dns.rrset
from task1_resolve import Resolver, ROOT_SERVERS
from task3_cache import YourCache
from task2_steering import measure
from analyze_floor import analyze
import bench


def reply(name, answers=(), authority=(), glue=(), aa=False):
    r = dns.message.make_response(dns.message.make_query(name, 'A'))
    if aa:
        r.flags |= dns.flags.AA
    for section, records in [(r.answer, answers), (r.authority, authority), (r.additional, glue)]:
        for owner, kind, value in records:
            rrset = dns.rrset.from_text(owner, 60, 'IN', kind, value)
            existing = next((rr for rr in section if rr.name == rrset.name and rr.rdtype == rrset.rdtype), None)
            if existing is not None:
                for item in rrset:
                    existing.add(item)
            else:
                section.append(rrset)
    return r


class ResolverTests(unittest.TestCase):
    def from_map(self, records, **kwargs):
        def query(name, server):
            value = records.get((name.to_text(), server), dns.exception.Timeout())
            if isinstance(value, Exception):
                raise value
            return value
        return Resolver(query=query, **kwargs)

    def test_no_glue_resolves_ns_from_root_and_records_extra_queries(self):
        name, ns = 'www.example.com.', 'ns.example.net.'
        records = {
            (name, ROOT_SERVERS[0]): reply(name, authority=[('com.', 'NS', ns)]),
            (ns, ROOT_SERVERS[0]): reply(ns, authority=[('net.', 'NS', 'ns.net.')],
                                      glue=[('ns.net.', 'A', '192.0.2.10')]),
            (ns, '192.0.2.10'): reply(ns, answers=[(ns, 'A', '192.0.2.11')], aa=True),
            (name, '192.0.2.11'): reply(name, answers=[(name, 'A', '192.0.2.99')], aa=True),
        }
        address, path = self.from_map(records).resolve(name)
        self.assertEqual(address, '192.0.2.99')
        self.assertEqual(path, [ROOT_SERVERS[0], ROOT_SERVERS[0], '192.0.2.10', '192.0.2.11'])

    def test_root_can_supply_cross_tld_glue(self):
        name = 'www.example.com.'
        records = {
            (name, ROOT_SERVERS[0]): reply(name, authority=[('com.', 'NS', 'ns.example.net.')],
                                         glue=[('ns.example.net.', 'A', '192.0.2.12')]),
            (name, '192.0.2.12'): reply(name, answers=[(name, 'A', '192.0.2.99')], aa=True),
        }
        self.assertEqual(len(self.from_map(records).resolve(name)[1]), 2)

    def test_timeout_tries_another_root(self):
        name = 'www.example.com.'
        records = {(name, ROOT_SERVERS[1]): reply(name, answers=[(name, 'A', '192.0.2.99')], aa=True)}
        self.assertEqual(self.from_map(records).resolve(name)[1], ROOT_SERVERS[:2])

    def test_partial_glue_failure_falls_back_to_ns_without_glue(self):
        name, ns = 'www.example.com.', 'ns.other.net.'
        records = {
            (name, ROOT_SERVERS[0]): reply(name, authority=[('com.', 'NS', 'dead.com.'), ('com.', 'NS', ns)],
                                         glue=[('dead.com.', 'A', '192.0.2.20')]),
            (ns, ROOT_SERVERS[0]): reply(ns, answers=[(ns, 'A', '192.0.2.21')], aa=True),
            (name, '192.0.2.21'): reply(name, answers=[(name, 'A', '192.0.2.99')], aa=True),
        }
        address, path = self.from_map(records).resolve(name)
        self.assertEqual(address, '192.0.2.99')
        self.assertIn('192.0.2.20', path)
        self.assertIn('192.0.2.21', path)

    def test_cname_restarts_at_root(self):
        name, target = 'www.example.com.', 'target.example.org.'
        records = {
            (name, ROOT_SERVERS[0]): reply(name, answers=[(name, 'CNAME', target)], aa=True),
            (target, ROOT_SERVERS[0]): reply(target, answers=[(target, 'A', '192.0.2.99')], aa=True),
        }
        self.assertEqual(self.from_map(records).resolve(name)[1], [ROOT_SERVERS[0], ROOT_SERVERS[0]])

    def test_cname_cycle_and_query_budget_stop(self):
        name, target = 'a.example.', 'b.example.'
        records = {
            (name, ROOT_SERVERS[0]): reply(name, answers=[(name, 'CNAME', target)], aa=True),
            (target, ROOT_SERVERS[0]): reply(target, answers=[(target, 'CNAME', name)], aa=True),
        }
        with self.assertRaises(RuntimeError):
            self.from_map(records).resolve(name)
        with self.assertRaisesRegex(RuntimeError, 'query limit'):
            self.from_map(records, max_queries=1).resolve(name)

    def test_transport_clears_rd_and_retries_truncated_response_over_tcp(self):
        name = dns.name.from_text('www.example.com.')
        truncated = reply(name)
        truncated.flags |= dns.flags.TC
        final = reply(name, answers=[(name, 'A', '192.0.2.99')], aa=True)
        with patch('dns.query.udp', return_value=truncated) as udp, patch('dns.query.tcp', return_value=final) as tcp:
            self.assertIs(Resolver()._query(name, ROOT_SERVERS[0]), final)
            self.assertFalse(udp.call_args.args[0].flags & dns.flags.RD)
            tcp.assert_called_once()


class CacheTests(unittest.TestCase):
    def test_expiration_boundary_and_case_equivalence(self):
        calls = []
        def upstream(name):
            calls.append(name)
            return str(len(calls)), 20
        cache = YourCache(upstream)
        self.assertEqual(cache.lookup('Example.COM.', 0), '1')
        self.assertEqual(cache.lookup('example.com', 19.999), '1')
        self.assertEqual(cache.lookup('example.com', 20), '2')
        self.assertEqual(len(calls), 2)

    def test_zero_ttl_never_reuses_answer(self):
        calls = []
        def upstream(name):
            calls.append(name)
            return str(len(calls)), 0
        cache = YourCache(upstream)
        self.assertEqual(cache.lookup('x', 0), '1')
        self.assertEqual(cache.lookup('x', 0), '2')

    def test_workload_matches_independent_floor(self):
        result = bench.run(YourCache, 'regression')
        self.assertEqual(result['stale'], 0)
        self.assertEqual(result['upstream'], analyze()['minimum_upstream'])
        self.assertEqual(result['upstream'], 275)


class MeasurementTests(unittest.TestCase):
    def test_collector_follows_in_message_cname_and_keeps_address_set(self):
        name = 'www.example.com'
        answer = reply(name, answers=[(name, 'CNAME', 'a.example.net.'),
                                     ('a.example.net.', 'A', '192.0.2.99')])
        with patch('dns.query.udp', return_value=answer):
            result = measure(name, '192.0.2.1')
        self.assertIsNone(result['error'])
        self.assertEqual(result['addresses'], ['192.0.2.99'])
        self.assertEqual(result['chain'][0]['to'], 'a.example.net')

    def test_timeout_is_unknown_not_an_empty_address_set(self):
        with patch('dns.query.udp', side_effect=dns.exception.Timeout):
            result = measure('www.example.com', '192.0.2.1')
        self.assertIsNone(result['addresses'])
        self.assertIsNotNone(result['error'])

    def test_real_capture_pairs_and_referral_sections(self):
        path = Path(__file__).parent / 'out' / 'capture.json'
        rows = json.loads(path.read_text(encoding='utf-8'))['dns_packets']
        queries = [row for row in rows if not row['response']]
        answers = [row for row in rows if row['response']]
        for answer in answers:
            self.assertTrue(any(q['id'] == answer['id'] and q['source'] == answer['destination']
                                and q['destination'] == answer['source'] for q in queries))
        self.assertTrue(any(row['delegation'] and row['answer_count'] == 0 for row in answers))
        self.assertTrue(any(row['a_answer'] for row in answers))


if __name__ == '__main__':
    unittest.main(verbosity=2)
