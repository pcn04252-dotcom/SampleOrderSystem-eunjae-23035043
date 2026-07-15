# PLAN: SampleOrderSystem

> 이 문서는 구현이 진행됨에 따라 갱신되는 living document입니다. 실제 구현 중 발견된 이슈나 구조 변경 사항, 단계 조정 사항을 반영해 계속 업데이트합니다. 상세 기능 요구사항은 `docs/PRD.md` 참고.

## 1. 목적

`docs/PRD.md` 3장(기능 명세)에 정의된 반도체 시료 생산주문관리 콘솔 시스템을 구현한다.

## 2. 기술 스택 및 설계 결정

- 언어: Python 3.x
- 아키텍처: MVC (Model / View / Controller)
- 영속성: SQLite (`sqlite3` 표준 라이브러리, 외부 의존성 없음). `PoC` repo(`DataPersistence`)에서 검증한 방식을 그대로 채택.
- DB 파일 경로: `data/app.db`
- 콘솔 UI 렌더링: [`rich`](https://github.com/Textualize/rich) 라이브러리 사용 (`requirements.txt`에 명시). 다른 PoC repo와 달리 이 repo는 **최종 산출물의 시각적 완성도**가 평가 요소이므로 외부 의존성을 허용한다 (6장 참고).

## 3. 설계 결정 사항

- **생산 진행 방식 — Clock 추상화 도입 (확정)**
  - PRD 예시 UI는 "진행률 72%, 완료 예정 09:49"처럼 시간 기반 진행을 보여주지만, 실제 벽시계 시간(수 분~수십 분)을 그대로 기다리게 하는 것은 비현실적이다.
  - `Clock` 인터페이스(`now()` 메서드 하나)를 두고, 생산 큐 로직은 항상 이 `Clock`을 통해서만 현재 시각을 확인한다.
  - 승인 시 `완료 예정 시각 = clock.now() + 총_생산시간`을 저장해두고, **생산라인 조회 등 아무 메뉴를 조회할 때마다** 현재 시각이 완료 예정 시각을 지났는지 lazy하게 확인해 지났으면 그 자리에서 `PRODUCING → CONFIRMED`로 전환한다 (백그라운드 스레드/타이머 불필요).
  - **실제 실행용**: `ScaledSystemClock` — 진짜 `datetime.now()`를 쓰되 배율을 곱한다. **배율: 실제 1초 = 시뮬레이션 1분** (예: 총 생산시간 165분 → 실제 대기 시간 약 165초). 배율은 설정값(`config.py` 등)으로 분리해 조정 가능하게 한다.
  - **테스트용**: `FakeClock` — 테스트 코드가 임의의 시각으로 즉시 이동시킬 수 있는 목(mock) 구현. 실제 대기 없이 상태 전이를 즉시 검증한다.
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
  queued_at TEXT NOT NULL,
  expected_completion_at TEXT  -- RUNNING 전환 시점에 계산되어 채워짐 (WAITING 동안은 NULL)
);
```

## 5. 폴더 구조

```
src/
  model/
    sample_model.py       # Sample CRUD, 검색, 재고 상태 분류(여유/부족/고갈)
    order_model.py        # Order 생성/상태 전이/승인 분기 로직
    order_status.py        # 주문 상태 변경 공통 헬퍼 (order_model/production_model이 공유, 순환 import 방지용)
    production_model.py   # 생산 큐(FIFO), 실생산량/생산시간 계산, Clock 기반 lazy 완료 판정
    clock.py              # Clock 인터페이스, ScaledSystemClock(1초=1분), FakeClock(테스트용)
    db.py                 # 연결 및 스키마 초기화
  view/
    console_view.py       # rich 기반 메뉴/표/배지/진행률 렌더링, 입력 수집
  controller/
    main_controller.py    # 메인 메뉴 라우팅 + 요약 정보
    sample_controller.py  # 시료 관리 (등록/조회/검색)
    order_controller.py   # OrderController(접수) + OrderApprovalController(승인/거절)
    monitoring_controller.py
    production_controller.py
    shipping_controller.py
  main.py                 # 진입점 (UTF-8 인코딩 고정, ScaledSystemClock 사용)
tests/
  test_clock.py             # FakeClock + 실제 ScaledSystemClock 테스트
  test_sample_model.py
  test_order_model.py
  test_production_model.py  # FIFO, Clock 기반 완료 판정 (FakeClock + 실제 ScaledSystemClock 통합 테스트 포함)
docs/
  PRD.md
requirements.txt          # rich
requirements-dev.txt      # pytest
```

## 6. 콘솔 UI 디자인 가이드라인

> 이 프로젝트는 md 문서만 보고 구현이 이어질 수 있으므로, 원본 과제 PDF의 예시 UI 화면(시각적 스타일)을 텍스트로 명시해둔다. 화면 "구성"(어떤 정보를 보여줄지)은 PRD 3장 각 절의 예시가 기준이고, 여기서는 그 화면들에 공통으로 적용되는 **시각적 스타일**을 규정한다.

원본 PDF 예시 화면들(메인 메뉴/시료 관리/시료 주문/주문 승인·거절/모니터링/생산라인/출고 처리)에서 반복적으로 나타나는 스타일 요소:

1. **구분선**: 화면 상단/섹션 사이에 `====...====` 형태의 구분선을 사용한다.
2. **메뉴 헤더**: `[번호] 메뉴명` 형식 (예: `[3] 주문 승인/거절`), 필요 시 우측에 타임스탬프 병기 (예: `[4] 모니터링  2026-04-16 09:32:15`).
3. **선택 프롬프트**: 항상 `선택 > ` 문자열로 입력을 유도한다.
4. **표(테이블)**: 컬럼이 정렬된 표 형태로 목록을 출력한다 (번호/ID/이름/수량/상태 등 컬럼 정렬).
5. **상태 배지(색상 구분)**: 주문/재고 상태를 값 그대로 출력하지 않고 색상이 있는 배지처럼 강조한다. 색상 매핑(고정):

   | 상태 | 색상 |
   |---|---|
   | `RESERVED` | 파란색/청록색 계열 (대기 중 느낌) |
   | `CONFIRMED` | 초록색 |
   | `PRODUCING` | 노란색/주황색 |
   | `REJECTED` | 빨간색 |
   | `RELEASE` | 보라색/자홍색 |
   | 재고 "여유" | 초록색 |
   | 재고 "부족" | 노란색/주황색 |
   | 재고 "고갈" | 빨간색 |

6. **상태 전이 표기**: `RESERVED → PRODUCING`처럼 화살표로 이전 상태와 다음 상태를 함께 보여준다.
7. **진행률 표시(생산라인)**: `[========          ] 72%` 형태의 텍스트 진행 바, 완료 예정 시각 병기.
8. **완료/성공 메시지 강조**: "예약 접수 완료.", "승인 완료.", "출고 처리 완료." 등 처리 완료 메시지는 일반 텍스트와 구분되도록(예: 초록색) 강조한다.

**구현 방법**: 위 스타일을 직접 ANSI 이스케이프 코드로 구현하는 대신 [`rich`](https://pypi.org/project/rich/) 라이브러리를 사용한다. `rich.table.Table`로 정렬된 표를, `rich.text.Text`/`rich.console.Console`의 스타일 인자로 상태 배지 색상을, `rich.progress`로 생산 진행률 바를 구현하면 위 스타일을 적은 코드로 재현할 수 있다. `view/console_view.py`에 상태→색상 매핑 상수를 두고 모든 렌더링 함수가 이를 참조하도록 하여 색상 일관성을 보장한다.

## 7. 구현 단계

- [x] Phase 0 — 프로젝트 셋업: SQLite 스키마 초기화(`db.py`), `Clock` 인터페이스/`ScaledSystemClock`/`FakeClock` 구현, `requirements.txt`(`rich`) 및 상태→색상 매핑 상수(`view/console_view.py`) 정의, 기본 MVC 골격.
- [x] Phase 1 — 시료 관리: 등록/조회/검색 (`PRD §3.2`).
- [x] Phase 2 — 시료 주문 접수: `RESERVED` 생성 (`PRD §3.3`).
- [x] Phase 3 — 주문 승인/거절: 재고 판정 분기(`CONFIRMED`/`PRODUCING`), 거절(`REJECTED`) (`PRD §3.4`).
- [x] Phase 4 — 생산 라인: FIFO 큐, `실 생산량 = ceil(부족분/수율)`, `총 생산시간 = 평균생산시간 × 실생산량`, `Clock` 기반 완료 예정 시각 계산 및 조회 시점 lazy 전이(`PRODUCING → CONFIRMED`) (`PRD §3.6`).
- [x] Phase 5 — 모니터링: 상태별 주문 집계(REJECTED 제외), 재고 상태(여유/부족/고갈) (`PRD §3.5`). **재고 상태 판정 기준 확정**: 고갈(재고 0) / 부족(현재 재고 < RESERVED+PRODUCING 주문 수량 합) / 여유(그 외).
- [x] Phase 6 — 출고 처리: `CONFIRMED → RELEASE` (`PRD §3.7`).
- [x] Phase 7 — 메인 메뉴 통합: 요약 정보(등록 시료 수, 총 재고, 전체 주문, 생산 대기) (`PRD §3.1`).
- [x] Phase 8 — 테스트 보강: 상태 전이, 계산식(부족분/실생산량/생산시간), FIFO 순서, `FakeClock` 단위 테스트 **및 실제 `ScaledSystemClock`으로 mocking 없이 real-time 경과를 검증하는 통합 테스트** 포함. 25개 테스트 전체 통과.
- [ ] Phase 9 — 예외 케이스 처리: PRD 6장(예외 처리 및 엣지 케이스) 항목 재점검 (현재 존재하지 않는 시료/주문 ID, 중복 시료 ID, 잘못된 상태 전이 시도 등은 반영됨 — 추가 리뷰 필요).

## 8. 완료 기준 (Definition of Done)

- [x] PRD 3장의 6개 기능 영역이 모두 콘솔에서 동작한다.
- [x] 주문 상태 전이가 PRD 2.3절 규칙을 정확히 따른다 (`REJECTED`/`RELEASE`는 종결 상태).
- [x] 생산 큐가 FIFO 순서를 보장한다.
- [x] 재고/생산량 계산식이 PRD 3.6절 공식과 일치한다.
- [x] 생산 완료 판정이 `Clock` 추상화를 통해서만 이뤄지며, `FakeClock` 단위 테스트와 **실제 `ScaledSystemClock` 통합 테스트** 양쪽으로 검증한다.
- [x] 모든 화면이 6장의 색상 매핑(상태별 배지 색상)을 일관되게 적용한다.
- [x] `pytest` 전체 통과 (25개).
- [x] 앱 재시작 후에도 데이터(시료/주문/생산큐)가 유지된다 (SQLite 파일 기반).
- [x] 전체 시나리오(시료 등록 → 주문 → 승인 → 생산 → 출고 → 모니터링)를 실제 `ScaledSystemClock`으로 실제 시간이 흐르는 상태에서 수동 검증 완료.

## 9. 변경 이력

- 최초 작성
- 생산 진행 방식을 `Clock` 추상화(실행: `ScaledSystemClock` 1초=1분 / 테스트: `FakeClock`)로 확정
- 콘솔 UI 디자인 가이드라인 추가 (`rich` 라이브러리 채택, 상태별 색상 매핑 고정)
- **구현 완료**: Model(sample/order/production/clock/order_status/db) → View(rich 기반 console_view) → Controller(main/sample/order/monitoring/production/shipping) → main.py 순으로 구현.
  - `order_status.py`를 추가로 도입 — `order_model`과 `production_model`이 서로를 참조해야 하는데(승인 시 생산 큐 등록, 생산 완료 시 주문 상태 변경) 상태 변경 로직을 여기로 분리해 순환 import를 피했다.
  - 재고 상태(여유/부족/고갈) 판정 기준을 "현재 재고 vs RESERVED+PRODUCING 주문 수량 합"으로 확정 (PRD에 구체적 임계값이 없어 자체 정의).
  - 생산 완료 시 재고 반영 공식: `재고 += 실생산량; 재고 -= 부족분` — 실생산량이 부족분보다 큰 경우(수율 보정 올림) 그 차액이 잉여 재고로 남는다.
  - 사용자 요청에 따라 `tests/test_clock.py`, `tests/test_production_model.py`에 **mocking이 아닌 실제 `ScaledSystemClock`으로 real-time 경과를 검증하는 테스트**를 추가 (생산시간을 아주 짧게 설정해 실제 대기는 수 초 이내로 유지).
  - 별도 드라이버 스크립트로 전체 메뉴 흐름(시료 등록 → 주문 접수 → 승인 → 생산 진행률 확인 → 실제 대기 후 완료 → 출고 → 모니터링)을 실제 프로세스로 실행해 수동 검증 완료.
- **PRD 대조 리뷰 및 수정**: PRD 전체(3장/4장/6장/2.3절) 대비 구현을 11개 항목으로 나눠 하나씩 검증. 10개 항목 PASS, 1개 항목(§3.7 출고 처리) PARTIAL 발견 후 수정.
  - 문제: PRD §3.7 "출고 시각, 출고 수량 등 처리 이력을 함께 기록/**표시**한다"에서 DB 기록은 정확했으나 화면 표시가 누락되어 있었음 (`shipping_controller.py`).
  - 수정: `ShippingController._release()`에서 `release_order` 호출 후 `order_model.get_order`로 갱신된 주문을 재조회해 출고수량/처리일시를 메시지에 포함하도록 변경.
- **Harness 도입** (미션2 평가 기준 2번 항목): `pyproject.toml`(pytest/ruff 설정), `requirements-dev.txt`에 `ruff` 추가, GitHub Actions CI(`.github/workflows/ci.yml`) 추가 — push/PR마다 `ruff check` + `pytest` 자동 실행.
  - `ruff check` 결과 발견된 이슈: 구식 `Optional[X]` 표기 6건(자동 수정), `E501`(줄 길이 100자 초과) 3건(수동 정리 — `db.py`의 CHECK 제약 줄바꿈, `sample_controller.py`의 리스트 표현식 분할, `test_clock.py`의 주석 분할). 도메인 로직 변경 없이 스타일만 정리.
