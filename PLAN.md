# PLAN: SampleOrderSystem

> 이 문서는 구현이 진행됨에 따라 갱신되는 living document입니다. 실제 구현 중 발견된 이슈나 구조 변경 사항, 단계 조정 사항을 반영해 계속 업데이트합니다. 상세 기능 요구사항은 `docs/PRD.md` 참고.

## 1. 목적

`docs/PRD.md` 3장(기능 명세)에 정의된 반도체 시료 생산주문관리 콘솔 시스템을 구현한다.

## 2. 기술 스택 및 설계 결정

- 언어: Python 3.x
- 아키텍처: MVC (Model / View / Controller)
- 영속성: SQLite (`sqlite3` 표준 라이브러리, 외부 의존성 없음). `PoC` repo(`DataPersistence`)에서 검증한 방식을 그대로 채택.
- DB 파일 경로: `data/app.db`

## 3. 미결정/열린 설계 사항 (구현 착수 전 확정 필요)

- **생산 진행 방식**: PRD의 예시 UI는 "진행률 72%, 완료 예정 09:49" 등 시간 기반 진행을 보여주지만, 콘솔 애플리케이션에서 실제 벽시계 시간(수 분~수십 분)을 그대로 기다리게 하는 것은 비현실적이다. 아래 중 하나로 확정 필요:
  - (A) 사용자가 "생산 진행" 메뉴를 선택할 때마다 큐의 다음 작업을 즉시 완료 처리 (턴제/수동 tick 방식)
  - (B) 실제 시간을 축소 비율로 시뮬레이션 (예: 1분 → 1초)로 백그라운드에서 진행
  - 현재 기본값: **(A) 수동 tick 방식**으로 진행하며, 추후 변경 가능.
- **동시 생산 라인 수**: PRD 상 "생산 라인 1개(단일 라인)"로 명시되어 있으므로 큐에는 항상 최대 1건만 RUNNING 상태를 가진다.

## 4. 데이터 모델 (SQLite 스키마 초안)

```sql
CREATE TABLE samples (
  sample_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  avg_production_time REAL NOT NULL,
  yield_rate REAL NOT NULL,
  current_stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
  order_id TEXT PRIMARY KEY,
  sample_id TEXT NOT NULL REFERENCES samples(sample_id),
  customer_name TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('RESERVED','REJECTED','PRODUCING','CONFIRMED','RELEASE')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  released_at TEXT
);

CREATE TABLE production_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  sample_id TEXT NOT NULL REFERENCES samples(sample_id),
  shortfall_quantity INTEGER NOT NULL,
  actual_production_quantity INTEGER NOT NULL,
  total_production_time REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('WAITING','RUNNING','DONE')),
  queued_at TEXT NOT NULL
);
```

## 5. 폴더 구조

```
src/
  model/
    sample_model.py       # Sample CRUD, 검색
    order_model.py        # Order 생성/상태 전이
    production_model.py   # 생산 큐(FIFO), 실생산량/생산시간 계산
    db.py                 # 연결 및 스키마 초기화
  view/
    console_view.py       # 메뉴 렌더링, 입력 수집, 표 출력
  controller/
    main_controller.py    # 메인 메뉴 라우팅
    sample_controller.py  # 시료 관리
    order_controller.py   # 주문 접수/승인/거절
    monitoring_controller.py
    production_controller.py
    shipping_controller.py
  main.py                 # 진입점
tests/
docs/
  PRD.md
```

## 6. 구현 단계

- [ ] Phase 0 — 프로젝트 셋업: SQLite 스키마 초기화(`db.py`), 기본 MVC 골격.
- [ ] Phase 1 — 시료 관리: 등록/조회/검색 (`PRD §3.2`).
- [ ] Phase 2 — 시료 주문 접수: `RESERVED` 생성 (`PRD §3.3`).
- [ ] Phase 3 — 주문 승인/거절: 재고 판정 분기(`CONFIRMED`/`PRODUCING`), 거절(`REJECTED`) (`PRD §3.4`).
- [ ] Phase 4 — 생산 라인: FIFO 큐, `실 생산량 = ceil(부족분/수율)`, `총 생산시간 = 평균생산시간 × 실생산량`, 생산 완료 시 `PRODUCING → CONFIRMED` (`PRD §3.6`).
- [ ] Phase 5 — 모니터링: 상태별 주문 집계(REJECTED 제외), 재고 상태(여유/부족/고갈) (`PRD §3.5`).
- [ ] Phase 6 — 출고 처리: `CONFIRMED → RELEASE` (`PRD §3.7`).
- [ ] Phase 7 — 메인 메뉴 통합: 요약 정보(등록 시료 수, 총 재고, 전체 주문, 생산 대기) (`PRD §3.1`).
- [ ] Phase 8 — 테스트 보강: 상태 전이, 계산식(부족분/실생산량/생산시간), FIFO 순서 단위 테스트.
- [ ] Phase 9 — 예외 케이스 처리: PRD 6장(예외 처리 및 엣지 케이스) 항목 전수 반영.

## 7. 완료 기준 (Definition of Done)

- PRD 3장의 6개 기능 영역이 모두 콘솔에서 동작한다.
- 주문 상태 전이가 PRD 2.3절 규칙을 정확히 따른다 (`REJECTED`/`RELEASE`는 종결 상태).
- 생산 큐가 FIFO 순서를 보장한다.
- 재고/생산량 계산식이 PRD 3.6절 공식과 일치한다.
- `pytest` 전체 통과.
- 앱 재시작 후에도 데이터(시료/주문/생산큐)가 유지된다.

## 8. 변경 이력

- (최초 작성 — 이후 구현 진행에 따라 추가)
