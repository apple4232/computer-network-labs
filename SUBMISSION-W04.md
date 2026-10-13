# Week 4 TCP 과제

제출 저장소: <https://github.com/apple4232/computer-network-labs>

현재 상태: Task 1/3 구현 및 검증 완료, Task 2 공식 trace 분석과 저녁 측정 완료. **2026-10-13 오후 9시 30분 KST에 예약한 두 번째 실측 대기 중이며 최종 제출 완료 상태는 아니다. 마감은 오늘 오후 10시다.**

- [관찰 기록](w04-tcp/out/observation.md): 과제별 3줄.
- [Task 2 보고서](w04-tcp/out/task2-report.md), [공식 TCP trace](w04-tcp/out/tcp.pcapng), [헤더 분석](w04-tcp/out/trace-analysis.json).
- [실제 처리량 측정](w04-tcp/out/throughput.json): 현재 1개 시간대 × 5회.
- [벤치마크](w04-tcp/out/bench.txt), [backoff 비교](w04-tcp/out/backoff-study.json).
- [과제 테스트](w04-tcp/out/test-tasks.txt), [추가 검증](w04-tcp/out/regression-tests.txt), [형식 검사](w04-tcp/out/check.txt).

Python 3.12, Windows에서 실행했다. Task 1은 selective repeat, Task 3은 slow start 이후 ACK 기반 완만한 증가와 0.65배 감소를 사용한다. `UnreliableChannel`, `bench.py`, `test_tasks.py`, `check.py`는 수정하지 않았다. 기본 신뢰성 fixture의 반복 바이트만으로는 순서 보존을 충분히 검사할 수 없어 별도 난수열 210개 전송을 검증했다.

Task 2는 캡처 도구가 없어 공식 9판 trace를 이용한 경로 B다. 한 네트워크만 사용할 수 있어 다른 시간대 실측 대안을 선택했다. 기록은 실제 수행 결과만 포함한다. `test_tasks.py`의 두 label 검사는 두 번째 측정 전까지 FAIL이고 tshark 검사는 설치되지 않아 SKIP이다. `check.py` 통과는 파일 형식 확인일 뿐 측정 완성을 의미하지 않는다.

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

두 번째 시간대에서 `python task2_measure.py --label "KT Wi-Fi / 2026-10-13 late evening KST"`를 실행하면 기존 JSON에 5회가 추가된다. 이후 관찰 기록과 보고서의 두 시간대 비교 및 검증 로그를 갱신한다. 자동 재측정은 이 채팅에 예약되어 있으며 완료하면 중지하도록 설정했다.

두 측정 사이 간격은 약 80분으로 계획되어 과제의 “매우 다른 시간대” 요건 충족은 불확실하다. 마감 안에 가능한 제한적 시간대 비교로 명시한다.
