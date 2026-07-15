# SampleOrderSystem

반도체 시료 생산주문관리 시스템 - 콘솔 기반 애플리케이션입니다.

- 언어: Python (`sqlite3` 표준 라이브러리 + `rich`)
- 상태: 구현 완료
- 기능 명세: [`docs/PRD.md`](./docs/PRD.md), 구현 계획: [`PLAN.md`](./PLAN.md), 세션 참고 문서: [`CLAUDE.md`](./CLAUDE.md)

## 실행 방법

```
pip install -r requirements.txt
python -m src.main
```

`data/app.db`에 시료/주문/생산 데이터가 저장되며, 다시 실행해도 이전 데이터가 유지됩니다.

## 테스트 방법

```
pip install -r requirements-dev.txt
pytest
```

## 주요 기능 (PRD 3장)

- 시료 관리 (등록/조회/검색)
- 시료 주문 접수
- 주문 승인/거절 (재고 충분 시 즉시 확정, 부족 시 생산 큐 자동 등록)
- 생산 라인 (FIFO, 실시간 진행률 표시)
- 모니터링 (상태별 주문 집계, 재고 상태 여유/부족/고갈)
- 출고 처리

## 검증한 것

- `pytest` 25개 테스트 통과 (상태 전이, 계산식, FIFO 순서, Clock 추상화)
- 생산 완료 판정은 `Clock` 추상화를 통해서만 이뤄지며, `FakeClock` 단위 테스트와 **mocking 없는 실제 `ScaledSystemClock` 통합 테스트**로 모두 검증
- 전체 시나리오(시료 등록 → 주문 접수 → 승인 → 생산 진행 → 실제 시간 경과 후 자동 완료 → 출고 → 모니터링)를 실제 프로세스로 실행해 수동 검증 완료
- 앱을 재시작해도 SQLite 데이터가 유지됨을 확인
