# CLAUDE.md

> 이 문서는 구현이 진행됨에 따라 갱신되는 living document입니다. 새 세션에서 이 repo를 열었을 때 아래 내용만으로 작업을 이어갈 수 있어야 합니다.

## 프로젝트 개요

반도체 시료 생산주문관리 콘솔 시스템. 기능 요구사항은 `docs/PRD.md`, 구현 계획은 `PLAN.md` 참고.

## 기술 스택

- Python 3.x + `sqlite3` (표준 라이브러리)
- 콘솔 UI 렌더링: `rich` (색상 배지/표/진행률 바 — `requirements.txt` 참고). 이 repo는 다른 PoC와 달리 시각적 완성도가 평가 대상이라 이 의존성만 예외적으로 허용한다.
- 아키텍처: MVC
- 테스트: `pytest` / 린트: `ruff` (설정은 `pyproject.toml`)
- CI: GitHub Actions (`.github/workflows/ci.yml`) — push/PR 시 `ruff check` + `pytest` 자동 실행

## 폴더 구조

```
src/model/
  db.py                # 연결/스키마 초기화
  clock.py             # Clock / ScaledSystemClock / FakeClock
  order_status.py      # 주문 상태 변경 공통 헬퍼 (order_model ↔ production_model 순환 import 방지)
  sample_model.py       # Sample CRUD/검색/재고 상태 분류
  order_model.py         # Order 생성/조회/승인(재고 분기)/거절/출고
  production_model.py    # 생산 큐(FIFO)/실생산량·생산시간 계산/lazy 완료 판정
src/view/console_view.py  # rich 기반 렌더링 (비즈니스 로직 금지, model import 금지)
src/controller/          # 메뉴 라우팅, Model-View 조율 (직접 SQL 금지)
src/main.py              # 진입점
tests/                   # model 계층 단위/통합 테스트
docs/PRD.md              # 기능 요구사항 원본
data/app.db              # 실제 데이터 (git 추적 제외)
```

## 실행 방법

```
pip install -r requirements.txt
python -m src.main
```

## 테스트 방법

```
pip install -r requirements-dev.txt
pytest
ruff check .
```

## 핵심 도메인 규칙 (PRD 요약, 상세는 docs/PRD.md 참고)

- 주문 상태: `RESERVED` → (`REJECTED` | `CONFIRMED` | `PRODUCING`) → `CONFIRMED` → `RELEASE`
- `REJECTED`는 모니터링 대상에서 제외한다.
- 부족분 = `max(0, 주문 수량 - 현재 재고)`
- 실 생산량 = `ceil(부족분 / 수율)`
- 총 생산 시간 = `평균 생산시간 × 실 생산량`
- 생산 완료 시 재고 반영: `재고 += 실생산량; 재고 -= 부족분` (실생산량 - 부족분 = 수율 보정으로 인한 잉여 재고)
- 재고 상태 분류(모니터링): 고갈(재고 0) / 부족(재고 < RESERVED+PRODUCING 주문 수량 합) / 여유(그 외)
- 생산 큐는 FIFO.
- 생산 라인은 단일 라인(동시 1건만 RUNNING).

## 코드 컨벤션

- `view`는 `model`을 직접 import하지 않는다 (controller를 통해서만 데이터 오감).
- 재고 차감/전이 등 상태 변경은 반드시 `model` 계층의 함수를 통해서만 수행한다 (controller에서 직접 SQL 실행 금지).
- SQL은 항상 파라미터 바인딩을 사용한다.
- 타입 힌트를 사용한다.
- 주석은 WHY가 비자명한 경우에만 한 줄로 작성한다.

## 생산 시간 처리 (Clock 추상화)

- 생산 완료 판정은 반드시 `src/model/clock.py`의 `Clock` 인터페이스를 통해서만 수행한다 — 코드에서 직접 `datetime.now()`를 호출하지 않는다.
- 실행 환경: `ScaledSystemClock(scale_seconds_per_minute=1.0)` (실제 1초 = 시뮬레이션 1분). `main.py`가 기본값으로 사용한다.
- 테스트 환경: 두 종류를 모두 사용한다.
  - `FakeClock`: 임의 시각으로 즉시 이동 가능한 목 구현. 대부분의 상태 전이 테스트에 사용 (실제 대기 없음).
  - `ScaledSystemClock`: mocking 없이 실제 시간 경과를 검증해야 할 때 사용 (`tests/test_clock.py`, `tests/test_production_model.py`). 실제 대기를 짧게 유지하려면 `avg_production_time`을 아주 작은 값(예: 0.02분)으로 설정하거나 `scale_seconds_per_minute`를 작게 주면 된다.
- 완료 판정은 백그라운드 스레드가 아니라, 아무 메뉴 조회 시점에 `완료 예정 시각`과 `clock.now()`를 비교하는 lazy 방식이다 (`production_model.sync_queue`).

## 콘솔 UI 디자인 (원본 PDF 예시 화면 재현 — 상세는 `PLAN.md` §6 참고)

md 문서만 보고 구현이 이어질 수 있으므로 색상 규칙을 항상 지킨다. 상태 배지 색상(고정, `view/console_view.py`에 상수로 정의):

| 상태 | 색상 |
|---|---|
| `RESERVED` | 파란색/청록색 |
| `CONFIRMED` | 초록색 |
| `PRODUCING` | 노란색/주황색 |
| `REJECTED` | 빨간색 |
| `RELEASE` | 보라색/자홍색 |
| 재고 "여유"/"부족"/"고갈" | 초록/노랑/빨강 |

그 외 스타일 규칙: `====` 구분선, `[번호] 메뉴명` 헤더, `선택 > ` 프롬프트, 정렬된 표, `A → B` 상태 전이 표기, 생산 진행률 바, 완료 메시지 강조. 새로운 화면을 추가할 때도 이 스타일을 그대로 따른다.

## 주의사항

- PRD 원본 슬라이드에는 출고 완료 상태가 `RELEASED`(플로우 다이어그램)와 `RELEASE`(상태표)로 다르게 표기되어 있다. 이 repo에서는 **`RELEASE`로 통일**한다 (`docs/PRD.md` §2.2 참고).
- 이 repo의 SQLite 스키마/영속성 방식은 `DataPersistence` PoC에서 검증한 패턴을 따르되, 코드/DB 파일을 직접 공유하지 않는 독립 repo이다.
- `main.py`에서 Windows 콘솔 기본 코드페이지(cp949) 한글 깨짐 방지를 위해 `sys.stdout.reconfigure(encoding="utf-8")` / `sys.stdin.reconfigure(encoding="utf-8")`를 적용한다 (`ConsoleMVC` PoC에서 확인된 이슈).
