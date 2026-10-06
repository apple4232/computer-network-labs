"""Analyze real interface captures, or clearly attributed official DNS traces."""
import argparse
import hashlib
import json
from pathlib import Path
import dns.flags
import dns.message
import dns.rdatatype
from scapy.all import IP, UDP, Dot11, PcapNgWriter, rdpcap

OUT = Path(__file__).parent / 'out'


def analyze(source, own=False, method='Windows SIO_RCVALL'):
    packets = rdpcap(str(source))
    selected, rows = [], []
    seen_packets = set()
    for original, packet in enumerate(packets, 1):
        if IP not in packet:
            # Packet Monitor may label native 802.11 NIC frames as Ethernet.
            wifi = Dot11(bytes(packet))
            if IP in wifi:
                wifi.time = packet.time
                packet = wifi
        if UDP not in packet or IP not in packet:
            continue
        udp = packet[UDP]
        if 53 not in (udp.sport, udp.dport):
            continue
        if own and 53003 not in (udp.sport, udp.dport):
            continue
        if own:
            # Stack-component copies are duplicates of the same real IP datagram.
            signature = (packet[IP].src, packet[IP].dst, udp.sport, udp.dport, bytes(udp.payload))
            if signature in seen_packets:
                continue
            seen_packets.add(signature)
        wire = bytes(udp.payload)
        try:
            msg = dns.message.from_wire(wire)
        except Exception:
            continue
        if own and not msg.question:
            raise RuntimeError('unexpected DNS packet without a question')
        selected.append(packet)
        rows.append({'packet': len(selected), 'original_packet': original,
                     'source': packet[IP].src, 'destination': packet[IP].dst,
                     'source_port': udp.sport, 'destination_port': udp.dport,
                     'id': f'0x{msg.id:04x}', 'response': bool(msg.flags & dns.flags.QR),
                     'dns_bytes': len(wire), 'frame_bytes': len(bytes(packet)),
                     'answer_count': sum(len(rr) for rr in msg.answer),
                     'authority_count': sum(len(rr) for rr in msg.authority),
                     'additional_count': sum(len(rr) for rr in msg.additional),
                     'message': msg.to_text(),
                     'delegation': not msg.answer and any(rr.rdtype == dns.rdatatype.NS for rr in msg.authority),
                     'a_answer': any(rr.rdtype == dns.rdatatype.A for rr in msg.answer)})
    if not any(not r['response'] for r in rows) or not any(r['response'] for r in rows):
        raise RuntimeError('capture lacks queries or responses')
    writer = PcapNgWriter(str(OUT / 'dns.pcapng'))
    for packet in selected:
        writer.write(packet)
    writer.close()
    result = {'source_file': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'own_interface_capture': own, 'capture_method': method if own else 'official trace', 'dns_packets': rows}
    (OUT / 'capture.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    response = max((r for r in rows if r['response']), key=lambda r: r['dns_bytes'])
    answer = next((r for r in rows if r['response'] and r['a_answer']), None)
    delegation = next((r for r in rows if r['response'] and r['delegation']), None)
    pair = next((r for r in rows if not r['response'] and answer and r['id'] == answer['id']
                 and r['source'] == answer['destination'] and r['destination'] == answer['source']), None)
    lines = ['# Packet evidence', '', '## Source and privacy', '']
    if own:
        lines += [f'Captured on this Windows PC using {method} on the active network interface.',
                  'Actual IP packet bytes were saved with the raw-IP link type (no Ethernet header was synthesized). '
                  'Duplicate observations with the same endpoint tuple and UDP payload were removed.',
                  'Only actual UDP packets with ports 53 and 53003 were retained. '
                  'Port 53003 was bound by our iterative resolver; background DNS traffic was excluded.']
    else:
        lines += ['Path (B): this is an official textbook trace, not traffic captured on this PC.',
                  f'Original file: `{source.name}`; SHA-256: `{result["source_sha256"]}`.',
                  'Only DNS packets were retained in dns.pcapng; original packet numbers are preserved in capture.json.',
                  'Wireshark lab trace files from J.F. Kurose and K.W. Ross, '
                  '*Computer Networking: A Top-Down Approach*, 9th ed. '
                  '[Author site](https://gaia.cs.umass.edu/kurose_ross/). '
                  'Copyright 1996-2025 J.F. Kurose, K.W. Ross. All Rights Reserved.',
                  '[9e trace source](https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces-9e.zip).']
    lines += ['', '## Query and matching answer', '']
    if pair:
        lines += [f'Query packet {pair["packet"]} (original {pair["original_packet"]}) and answer packet '
                  f'{answer["packet"]} (original {answer["original_packet"]}) share transaction ID `{answer["id"]}`.',
                  f'Query direction: `{pair["source"]}:{pair["source_port"]}` → '
                  f'`{pair["destination"]}:{pair["destination_port"]}`; response reverses it.',
                  f'The client host is {pair["source"]}. '
                  + ('This is our PC.' if own else 'It belongs to the published trace, not the student; the query source identifies the client, but not its human owner.')]
    lines += ['', '## Delegation versus answer', '']
    if delegation:
        lines += [f'Delegation: packet {delegation["packet"]}; ANCOUNT={delegation["answer_count"]}, '
                  f'authority section contains NS records. Answer: packet {answer["packet"]}; '
                  f'ANCOUNT={answer["answer_count"]}, A record in the answer section.']
    else:
        lines += ['This trace contains no zero-answer NS referral. A3 cannot be demonstrated from this capture.',
                  'An NS reply with records in the answer section is not a delegation. '
                  'Live resolve-korea.json separately documents root → kr → korea.ac.kr referrals, '
                  'but that JSON is not an interface capture.']
    lines += ['', '## Largest DNS response', '',
              f'Packet {response["packet"]} (original {response["original_packet"]}): '
              f'**{response["dns_bytes"]} DNS-message bytes** (excluding UDP/IP/Ethernet headers); '
              f'{response["frame_bytes"]} captured packet bytes (here the IP datagram).',
              f'It contains {response["answer_count"]} answer RRs, '
              f'{response["authority_count"]} authority RRs, '
              f'{response["additional_count"]} additional RRs. '
              'The record names and resource data below explain its size:', '',
              '```text', response['message'], '```', '',
              '## Retained packet map', '',
              '| Output packet | Original packet | Direction | Transaction ID | DNS bytes | Answers | Authority | Additional |',
              '|---:|---:|---|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['packet']} | {row['original_packet']} | {'response' if row['response'] else 'query'} | "
                     f"{row['id']} | {row['dns_bytes']} | {row['answer_count']} | {row['authority_count']} | {row['additional_count']} |")
    (OUT / 'capture-analysis.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'{len(rows)} actual DNS packets; delegation={bool(delegation)}; largest={response["dns_bytes"]} DNS bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--own', action='store_true')
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    analyze(args.source, args.own)
