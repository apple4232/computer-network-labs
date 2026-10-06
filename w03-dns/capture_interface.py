"""Windows administrator capture of actual IP datagrams on our active interface.

Windows SIO_RCVALL collects real IP packets; no packet headers are synthesized.
Only our resolver's UDP port 53003 paired with remote DNS port 53 is saved.
"""
from pathlib import Path
import os
import socket
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'


def main():
    local_deps = HERE.parent / '.lab-deps'
    if local_deps.is_dir():
        sys.path.insert(0, str(local_deps))
        os.environ['PYTHONPATH'] = str(local_deps)
    from scapy.all import IP, UDP, PcapNgWriter
    OUT.mkdir(exist_ok=True)
    route = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    route.connect(('198.41.0.4', 53))
    local = route.getsockname()[0]
    route.close()
    receiver = None
    packets = []
    stop = threading.Event()
    thread = None
    try:
        receiver = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        receiver.bind((local, 0))
        receiver.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        receiver.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        receiver.settimeout(0.2)

        def receive():
            while not stop.is_set():
                try:
                    wire, _ = receiver.recvfrom(65535)
                except socket.timeout:
                    continue
                packet = IP(wire)
                if (UDP in packet and {packet[UDP].sport, packet[UDP].dport} == {53, 53003}
                        and local in (packet.src, packet.dst)):
                    packet.time = time.time()
                    packets.append(packet)

        thread = threading.Thread(target=receive, daemon=True)
        thread.start()
        with (OUT / 'capture-run.txt').open('w', encoding='utf-8') as log:
            for name, logfile in [('www.korea.ac.kr', 'resolve-korea.json'), ('dns.google', 'resolve-google.json')]:
                result = subprocess.run([sys.executable, str(HERE / 'task1_resolve.py'), name,
                                         '--source-port', '53003', '--log', str(OUT / logfile)],
                                        capture_output=True, text=True)
                log.write(result.stdout + result.stderr)
                if result.returncode:
                    raise RuntimeError('resolver failed during interface capture')
        stop.set()
        thread.join(2)
        writer = PcapNgWriter(str(OUT / 'own-dns-raw.pcapng'))
        for packet in packets:
            writer.write(packet)
        writer.close()
        from capture_analysis import analyze
        analyze(OUT / 'own-dns-raw.pcapng', own=True)
        (OUT / 'capture-status.txt').write_text(f'complete: Windows SIO_RCVALL; interface={local}; datagrams={len(packets)}', encoding='utf-8')
    except Exception as exc:
        (OUT / 'capture-status.txt').write_text(repr(exc), encoding='utf-8')
    finally:
        stop.set()
        if thread:
            thread.join(2)
        if receiver:
            receiver.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            receiver.close()


if __name__ == '__main__':
    main()
