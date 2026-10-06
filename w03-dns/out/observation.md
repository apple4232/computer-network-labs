# Week 3 관찰 기록

## Task 1
루트는 개별 호스트의 A 주소 대신 TLD의 NS와 glue를 제공하므로 직접 위임을 따라가야 한다. 실제 www.korea.ac.kr 조회는 루트 → kr → korea.ac.kr의 3회 질의로 끝났다.
glue가 없으면 NS 이름을 루트부터 별도로 해석하고 원래 조회를 이어 간다. 재현 가능한 no-glue 테스트에서는 NS 주소 해석에 2회가 추가되어 총 4회였으며, 실패한 서버와 부분 glue도 다음 후보로 재시도했다.
지정된 다섯 이름은 독립적인 시스템 recursive resolver 응답과 5/5 일치했다. Windows에 dig가 없어 dnspython 비교를 사용했으며, CNAME 재시작·TCP fallback·순환/질의 제한은 별도 테스트로 확인했다.

## Task 2
직접 캡처한 DNS 12개 중 packet 2는 ANCOUNT=0이고 authority에 NS가 있는 위임, packet 6은 answer에 A가 있는 최종 응답이었다. query 5/response 6의 ID는 0xde00이며, 가장 큰 응답은 NS 5개와 A/AAAA glue 10개를 담은 384바이트였다.
외부 CDN suffix와 운영자 정보를 함께 적용했다. 단순 마지막 두 label 비교는 www.wikipedia.org → dyna.wikimedia.org를 third party로 오판하지만 둘 다 Wikimedia 운영이며, 초기 suffix 목록의 Stanford/Netlify 누락도 수정했다.
세 resolver 비교는 CDN 9개 중 7개가 다른 A 집합을 반환했다. 두 번째 네트워크가 없어 경로 (B)로 국내 ISP와 NSID가 gpdns-nrt인 Google을 비교하면 5/9이며, DNS 응답 중앙값은 10.15/37.13ms였다. 주소 차이만으로 실제 가까운 replica나 네트워크 이동 효과를 증명할 수는 없다.

## Task 3
baseline의 고정 60초는 짧은 TTL을 넘겨 만료 주소를 반환하고 긴 TTL은 조기 폐기하며, 리스트 선형 탐색도 낭비다. dictionary와 개별 만료시각으로 바꾸니 upstream 325→275, stale 266→0, simulated time 6.5→5.5초였다.
정확한 하한은 275회다. 이름별 최초 질의와 이전 응답의 TTL이 끝난 뒤 첫 질의는 반드시 새 upstream 응답이 필요하며, 그 시각에 가져오면 다음 TTL 구간을 가장 길게 덮는다. 이 강제 구간을 독립적으로 세면 118+76+37+23+11+6+1+1+1+1=275다.
baseline이 가장 잘못 처리한 레코드는 TTL 20초인 www.microsoft.com으로, 만료 응답 189건(CNN 77건)을 만들었다. fixture에서 주소가 일정해 보여도 TTL 이후 변경 가능성을 무시해 이전 응답을 재사용할 수 없다.
