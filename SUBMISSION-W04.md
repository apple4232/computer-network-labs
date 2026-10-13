# Week 4 TCP 과제

제출 저장소: <https://github.com/apple4232/computer-network-labs>

현재 상태: Task 1/3 구현·검증, Task 2 공식 trace 분석·두 시점 실측·비교 보고서를 2026-10-13 22:00 KST 마감 전에 작성했다. 두 시점은 같은 KT Wi-Fi의 20:10/21:35이며 약 84분 간격이라는 실험 한계가 있다.

- [관찰 기록](w04-tcp/out/observation.md): 과제별 3줄.
- [Task 2 보고서](w04-tcp/out/task2-report.md), [공식 TCP trace](w04-tcp/out/tcp.pcapng), [헤더 분석](w04-tcp/out/trace-analysis.json).
- [실제 처리량 측정](w04-tcp/out/throughput.json): 같은 네트워크의 두 시점 × 5회, 총 10회.
- [벤치마크](w04-tcp/out/bench.txt), [backoff 비교](w04-tcp/out/backoff-study.json).
- [과제 테스트](w04-tcp/out/test-tasks.txt), [추가 검증](w04-tcp/out/regression-tests.txt), [형식 검사](w04-tcp/out/check.txt).

Python 3.12, Windows에서 실행했다. Task 1은 selective repeat, Task 3은 slow start 이후 ACK 기반 완만한 증가와 0.65배 감소를 사용한다. `UnreliableChannel`, `bench.py`, `test_tasks.py`, `check.py`는 수정하지 않았다. 기본 신뢰성 fixture의 반복 바이트만으로는 순서 보존을 충분히 검사할 수 없어 별도 난수열 210개 전송을 검증했다.

Task 2는 캡처 도구가 없어 공식 9판 trace를 이용한 경로 B다. 한 네트워크만 사용할 수 있어 다른 시간대 실측 대안을 선택했다. 기록은 실제 수행 결과만 포함한다. `test_tasks.py`는 7 passed, 0 failed, 2 skipped이며 `check.py w04`도 통과했다. tshark 미설치에 따른 캡처 검사와 사람이 평가하는 관찰문 항목은 SKIP이다. trace는 별도 분석기로 확인했다. 두 label은 두 네트워크가 아니라 두 시점이며, 자동 검사 통과가 “매우 다른 시간대” 조건 충족을 보증하지 않는다.

```powershell
cd w04-tcp
python task1_rdt.py --verify
python task1_rdt.py --verify --seed 999
python bench.py --yours
python study_backoff.py
python analyze_trace.py
python test_regressions.py
python test_tasks.py
python ../check.py w04
```

두 번째 실측은 `python task2_measure.py --label "KT Wi-Fi / 2026-10-13 late evening KST"`로 수행했고 기존 기록을 보존하여 5회를 추가했다. 처리량 중앙값은 48.79→56.82 Mbps, TCP 연결시간 중앙값은 10.74→10.85 ms다. 관찰 기록·비교 보고서·검증 로그를 갱신했다.

두 측정 사이 실제 간격은 약 84분으로 과제의 “매우 다른 시간대” 요건 충족은 불확실하다. 마감 안에 가능한 제한적 시간대 비교이며 두 개의 서로 다른 네트워크를 측정했다고 주장하지 않는다.
