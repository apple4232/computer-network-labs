# Week 3 DNS 과제 제출

제출 저장소: <https://github.com/apple4232/CN>

원본 실습: <https://github.com/codingchild2424/2026-lecture-network-practice>, 기준 커밋 `0ee3e66`.

## 제출 결과

- [관찰 기록](w03-dns/out/observation.md): 과제별 3줄.
- [측정 보고서](w03-dns/out/report.md), [실제 인터페이스 캡처](w03-dns/out/dns.pcapng), [패킷 분석](w03-dns/out/capture-analysis.md).
- [12개 사이트 × 3 resolver 원본 응답](w03-dns/out/chains.json).
- [캐시 벤치마크](w03-dns/out/bench.txt), [275회 하한 증명](w03-dns/out/cache-analysis.md).
- [다섯 이름 검증](w03-dns/out/verify.txt), [추가 경계조건 테스트](w03-dns/out/regression-tests.txt).

## 실행

Python 3.12에서 실행했다. 일반 환경에서는 다음과 같이 의존성을 설치한다.

```bash
cd w03-dns
python -m pip install -r requirements.txt
python task1_resolve.py --verify
python task2_steering.py --collect --network actual-network-name
python task2_steering.py --report
python bench.py --yours
python test_regressions.py
python test_tasks.py
python ../check.py w03
```

`dig`가 있으면 기존 검증 방식으로 비교한다. 이 Windows PC에는 `dig`가 없어 `--verify`에서 dnspython의 시스템 recursive resolver를 독립적인 비교 기준으로 사용했고 5/5가 일치했다. 제공된 `test_tasks.py`의 dig/tshark 검사는 도구가 없으면 skip하므로 별도 테스트와 실제 캡처 분석 결과도 함께 제출한다. `bench.py`, `test_tasks.py`, `check.py`는 원본 그대로다.

실제 캡처는 이 PC의 활성 인터페이스에 Windows `SIO_RCVALL` 캡처 소켓을 열고, 해석기가 사용한 UDP 53003과 DNS 53 포트의 패킷만 저장했다. IP 헤더를 합성하거나 질의/응답을 만들어 넣지 않았다. 캡처에서 백그라운드 도메인이 제외되었음을 확인했다. 재현하려면 의존성을 설치한 Windows 관리자 터미널에서 `python capture_interface.py`를 실행한다. 일반 과제 실행에는 관리자 권한이 필요 없다.

두 번째 물리적 네트워크는 사용할 수 없다는 학생 답변에 따라 Task 2의 **경로 (B)**를 적용했다. 국내 ISP DNS와 Google NRT 응답 지점의 거리 차이를 NSID와 응답 시간으로 확인했다. 모든 세 resolver 비교는 **7/9**, ISP–Google 비교만 하면 **5/9**다. 동일 PC의 네트워크 이동이나 선택된 CDN replica의 가까움을 직접 증명한 실험으로 서술하지 않았다.

원본의 `*/out/`와 캡처 제외 규칙에는 이번 제출 폴더만 예외를 추가했다. `w03-dns/out/`가 실제로 커밋되며, 다른 주차 실습은 원본 상태로 남아 있다.
