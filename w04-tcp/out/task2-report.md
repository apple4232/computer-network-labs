# Task 2 — 경로 B 분석 및 실측

상태: 공식 trace 분석과 저녁 5회 실측 완료. **두 번째 실측 전이므로 B1/B3의 두 시간대 비교는 미완료**다. 학생이 사용 가능한 네트워크가 하나뿐이라고 확인하여 과제의 다른 시간대 대안을 사용한다.

## A. 공식 TCP trace

출처: [교재 공식 Wireshark 실습](https://gaia.cs.umass.edu/kurose_ross/wireshark.php)의 [9판 trace ZIP](https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces-9e.zip), `tcp-wireshark-trace1-1.pcapng`.
원본을 변경 없이 `tcp.pcapng`로 저장했다. SHA-256: `164d5e3b3d2a25edb2ab6c57292e883c9c29123d4c18b2f5872a929f724559b3`.
표준 라이브러리 기반 `analyze_trace.py`로 pcapng의 프레임 번호, IPv4/TCP 헤더 및 옵션을 읽었으며 세부 수치는 `trace-analysis.json`에 저장했다. 이 분석기는 이 trace의 Ethernet/IPv4 형식을 대상으로 한다.

| 항목 | 관측 결과 |
|---|---|
| 클라이언트 | 192.168.86.68:55639 |
| 서버 | 128.119.245.12:80 |
| SYN | #1, seq=4236649187 |
| SYN-ACK | #2, seq=1068969752, ack=4236649188 |
| ACK | #3, seq=4236649188, ack=1068969753 |
| SYN→SYN-ACK / SYN→ACK | 22.414 ms / 22.505 ms |
| 클라이언트 SYN 옵션 | MSS 1460, WS shift 6 → ×64, SACK permitted |
| 서버 SYN-ACK 옵션 | MSS 1460, WS shift 7 → ×128, SACK permitted |
| 클라이언트 #3 수신 윈도 | raw 2058 ×64 = 131712 bytes |
| 업로드 최대 bytes in flight | #145: 75296 bytes; 그때 서버의 최신 수신 윈도 173824 bytes |
| 서버의 전송 중 수신 윈도 범위 | 31872–194816 bytes |

SYN의 윈도 값 자체에는 배율을 적용하지 않는다. 두 SYN에서 합의한 배율은 후속 세그먼트의 수신 윈도에 적용한다. 실제 sequence number는 Wireshark의 상대 번호 0과 구별했다. SYN이 번호 하나를 소비하므로 ACK는 ISN+1을 확인한다.

bytes in flight는 방향별로 관측한 가장 높은 데이터 끝 번호에서 반대 방향의 가장 높은 누적 ACK를 뺀 값이다. 이 trace에는 sequence wrap이 없으며 SACK 기반 부분 확인을 별도로 빼지 않은 관측치다. 업로드 최대치 75296 B는 당시 서버 rwnd 173824 B의 약 43.3%다. 따라서 그 순간 flow control 한도를 다 쓰지는 않았다. 실제 cwnd는 패킷 헤더에 없으므로 혼잡 윈도, ACK 왕복 지연, 응용 전송 패턴 중 정확한 병목을 단정하지 않는다.

패킷 내용에는 `POST /wireshark-labs/lab3-1-reply.htm`, `Host: gaia.cs.umass.edu`, Mac OS X 10.15/Firefox 85의 User-Agent, 업로드 파일명 `alice.txt`가 있다. 캡처 시각은 2021-02-03 UTC다. 즉 교재에 제공된 다른 호스트의 HTTP 업로드이며, 2026년 이 Windows PC에서 실행한 HTTPS 다운로드가 아니다. 패킷만으로 사용자 개인의 신원이나 교재 저자 본인의 전송인지는 확정할 수 없다.

## B. 같은 네트워크의 다른 시간대 측정

대상은 원본 지정 URL `https://speed.cloudflare.com/__down?bytes=5000000`이며 변경하지 않았다. 각 run마다 새 curl 프로세스로 HTTP/1.1 TCP 연결을 만들고 정확히 5,000,000 bytes와 HTTP 200을 확인한다. HTTP 오류·미완료 응답은 측정에 넣지 않는다. 시간은 Asia/Seoul(UTC+09:00)로 기록한다.

| 실제 측정 | 반복 | 중앙값 Mbps | 최소–최대 Mbps | 폭/중앙값 | TCP 연결시간 중앙값 |
|---|---:|---:|---:|---:|---:|
| KT Wi-Fi, 2026-10-13 20:10 KST | 5 | 48.79 | 38.64–53.63 | 30.7% | 10.74 ms |
| KT Wi-Fi, 2026-10-13 21:30 KST 예정 | 미실행 | — | — | — | — |

첫 실행의 Mbps는 48.79, 38.64, 53.63, 51.04, 46.36이었다. 각 run의 원시 시간은 `throughput.json`에 있다. throughput은 다운로드 bytes×8 / curl total 시간으로, DNS·TCP·TLS·서버 대기를 포함한 작은 객체의 종단 간 유효 속도이며 회선의 순수 최대 용량이 아니다. 연결시간은 `time_connect - time_namelookup`이고, `ttfb_s`는 연결 후 TLS 협상과 서버 응답 대기를 포함한다.

같은 연결에서도 Wi-Fi 경쟁, 경로 큐, 서버 응답, DNS 캐시 및 혼잡 제어의 초기 상태가 달라져 분산이 생길 수 있다. 이는 가능한 설명이며 다섯 번의 측정만으로 각각의 기여도를 분리하지 못한다. RTT가 크면 slow start에서 ACK를 기다리는 주기가 길어지고 같은 cwnd에서 cwnd/RTT가 낮아져 특히 작은 전송이 느려질 수 있다. 두 번째 기록이 없으므로 실제 시간대 간 연결시간·속도 관계는 아직 평가하지 않았다.

동일 네트워크의 시간대 비교는 서로 다른 접속망의 차이를 입증하지 못한다. 당일 21:30 측정 후 두 중앙값과 분산을 비교하되 시간대의 혼잡·서버 변화를 함께 고려한다. 공식 trace의 RTT와 이 PC의 처리량은 서로 다른 전송이므로 직접 대응시키지 않는다.

## 출처 표기

Wireshark lab trace files from J.F. Kurose and K.W. Ross,
*Computer Networking: A Top-Down Approach*, 9th ed.
<https://gaia.cs.umass.edu/kurose_ross/>
Copyright 1996-2025 J.F. Kurose, K.W. Ross. All Rights Reserved.

마감(2026-10-13 22:00 KST)에 맞춰 재측정을 당일 21:30으로 앞당겼다. 첫 측정과 약 80분 차이에 불과하므로 과제가 제시한 “매우 다른 시간대” 대안에 충분하지 않을 수 있으며, 실측 시각과 한계를 그대로 공개한다.
