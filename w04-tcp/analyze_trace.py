"""Read the official Ethernet/IPv4 TCP pcapng using only the standard library."""
import hashlib
import json
import socket
import struct
from pathlib import Path

OUT = Path(__file__).parent / 'out'


def packets(path):
    raw = path.read_bytes()
    offset = number = 0
    endian = '<'
    interfaces = []
    while offset < len(raw):
        if raw[offset:offset + 4] == b'\x0a\x0d\x0d\x0a':
            endian = '<' if raw[offset + 8:offset + 12] == b'\x4d\x3c\x2b\x1a' else '>'
            interfaces = []
        kind, length = struct.unpack_from(endian + 'II', raw, offset)
        if length < 12 or offset + length > len(raw):
            raise ValueError('Invalid pcapng block')
        assert struct.unpack_from(endian + 'I', raw, offset + length - 4)[0] == length
        body = raw[offset + 8:offset + length - 4]
        if kind == 1:
            link = struct.unpack_from(endian + 'H', body)[0]
            resolution = 1e-6
            pos = 8
            while pos + 4 <= len(body):
                code, size = struct.unpack_from(endian + 'HH', body, pos)
                val = body[pos + 4:pos + 4 + size]
                if code == 9:
                    resolution = 2 ** -(val[0] & 127) if val[0] & 128 else 10 ** -val[0]
                pos += 4 + ((size + 3) // 4) * 4
                if code == 0:
                    break
            interfaces.append((link, resolution))
        elif kind == 6:
            number += 1
            iface, hi, lo, caplen, original = struct.unpack_from(endian + 'IIIII', body)
            link, resolution = interfaces[iface]
            assert link == 1, 'Expected Ethernet'
            frame = body[20:20 + caplen]
            if len(frame) >= 34 and frame[12:14] == b'\x08\x00':
                ip = frame[14:]
                ihl = (ip[0] & 15) * 4
                if ip[9] == 6 and len(ip) >= ihl + 20:
                    tcp = ip[ihl:]
                    srcport, dstport, seq, ack = struct.unpack_from('!HHII', tcp)
                    thl = (tcp[12] >> 4) * 4
                    options = {}
                    pos = 20
                    while pos < thl:
                        code = tcp[pos]
                        if code == 0:
                            break
                        if code == 1:
                            pos += 1
                            continue
                        size = tcp[pos + 1]
                        if size < 2:
                            raise ValueError('Bad TCP option')
                        val = tcp[pos + 2:pos + size]
                        if code == 2:
                            options['mss'] = int.from_bytes(val, 'big')
                        elif code == 3:
                            options['window_scale_shift'] = val[0]
                        elif code == 4:
                            options['sack_permitted'] = True
                        pos += size
                    payload_len = int.from_bytes(ip[2:4], 'big') - ihl - thl
                    yield {'number': number, 'time': ((hi << 32) | lo) * resolution,
                           'src': socket.inet_ntoa(ip[12:16]), 'dst': socket.inet_ntoa(ip[16:20]),
                           'sport': srcport, 'dport': dstport, 'seq': seq, 'ack': ack,
                           'flags': tcp[13], 'window': int.from_bytes(tcp[14:16], 'big'),
                           'options': options, 'payload_bytes': payload_len}
        offset += length


def main():
    path = OUT / 'tcp.pcapng'
    rows = list(packets(path))
    syn = next(p for p in rows if p['flags'] & 0x12 == 0x02)
    client = (syn['src'], syn['sport'])
    server = (syn['dst'], syn['dport'])
    flow = [p for p in rows if ((p['src'], p['sport']), (p['dst'], p['dport']))
            in ((client, server), (server, client))]
    synack = next(p for p in flow if p['flags'] & 0x12 == 0x12)
    ack = next(p for p in flow if p['number'] > synack['number']
               and (p['src'], p['sport']) == client and p['flags'] & 0x10
               and p['ack'] == (synack['seq'] + 1) % 2**32)
    negotiated = all('window_scale_shift' in p['options'] for p in (syn, synack))
    shifts = {client: syn['options'].get('window_scale_shift', 0) if negotiated else 0,
              server: synack['options'].get('window_scale_shift', 0) if negotiated else 0}
    high = {client: syn['seq'] + 1, server: synack['seq'] + 1}
    acked = dict(high)
    windows = {client: syn['window'], server: synack['window']}
    peaks = {client: {'bytes': 0}, server: {'bytes': 0}}
    advertised = {client: [], server: []}
    for p in flow:
        src = (p['src'], p['sport'])
        dst = server if src == client else client
        if not p['flags'] & 2:
            windows[src] = p['window'] * 2 ** shifts[src]
            advertised[src].append(windows[src])
        if p['flags'] & 0x10:
            acked[dst] = max(acked[dst], p['ack'])
        if p['payload_bytes']:
            high[src] = max(high[src], p['seq'] + p['payload_bytes'])
            flight = max(0, high[src] - acked[src])
            if flight > peaks[src]['bytes']:
                peaks[src] = {'bytes': flight, 'packet': p['number'],
                              'receiver_advertised_window': windows[dst]}
    result = {'source': 'Official 9e archive / tcp-wireshark-trace1-1.pcapng (path B; not our traffic)',
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'tcp_packets': len(rows), 'flow_packets': len(flow),
              'syn': syn, 'syn_ack': synack, 'ack': ack,
              'handshake_ms': (ack['time'] - syn['time']) * 1000,
              'window_scaling_negotiated': negotiated,
              'client': {'peak_flight': peaks[client], 'scale_factor': 2 ** shifts[client],
                         'advertised_window_min': min(advertised[client]), 'advertised_window_max': max(advertised[client])},
              'server': {'peak_flight': peaks[server], 'scale_factor': 2 ** shifts[server],
                         'advertised_window_min': min(advertised[server]), 'advertised_window_max': max(advertised[server])}}
    (OUT / 'trace-analysis.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
