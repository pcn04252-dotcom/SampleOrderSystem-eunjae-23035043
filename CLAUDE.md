# CLAUDE.md

> 이 문서는 구현이 진행됨에 따라 갱신되는 living document입니다. 새 세션에서 이 repo를 열었을 때 아래 내용만으로 작업을 이어갈 수 있어야 합니다.

## 프로젝트 개요

반도체 시료 생산주문관리 콘솔 시스템. 기능 요구사항은 `docs/PRD.md`, 구현 계획은 `PLAN.md` 참고.

## 기술 스택

- Python 3.x + `sqlite3` (표준 라이브러리, 외부 의존성 없음)
- 아키텍처: MVC
- 테스트: `pytest`

## 폴더 구조

```
src/model/       # Sample/Order/Production 도메인 로직 + DB 접근 (I/O 없음, DB 접근은 예외)
src/view/        # 콘솔 렌더링/입력 (비즈니스 로직 금지)
src/controller/  # 메뉴 라우팅, Model-View 조율
src/main.py      # 진입점
tests/
docs/PRD.md      # 기능 요구사항 원본
data/app.db      # 실제 데이터 (git 추적 제외)
```

## 실행 방법

```
python -m src.main
```

## 테스트 방법

```
pytest
```

## 핵심 도메인 규칙 (PRD 요약, 상세는 docs/PRD.md 참고)

- 주문 상태: `RESERVED` → (`REJECTED` | `CONFIRMED` | `PRODUCING`) → `CONFIRMED` → `RELEASE`
- `REJECTED`는 모니터링 대상에서 제외한다.
- 부족분 = `max(0, 주문 수량 - 현재 재고)`
- 실 생산량 = `ceil(부족분 / 수율)`
- 총 생산 시간 = `평균 생산시간 × 실 생산량`
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
- 실행 환경: `ScaledSystemClock` (실제 1초 = 시뮬레이션 1분, 배율은 설정값으로 분리).
- 테스트 환경: `FakeClock` (임의 시각으로 즉시 이동 가능한 목 구현) — 실제 대기 없이 상태 전이를 검증한다.
- 완료 판정은 백그라운드 스레드가 아니라, 아무 메뉴 조회 시점에 `완료 예정 시각`과 `clock.now()`를 비교하는 lazy 방식이다.

## 주의사항

- PRD 원본 슬라이드에는 출고 완료 상태가 `RELEASED`(플로우 다이어그램)와 `RELEASE`(상태표)로 다르게 표기되어 있다. 이 repo에서는 **`RELEASE`로 통일**한다 (`docs/PRD.md` §2.2 참고).
- 이 repo의 SQLite 스키마/영속성 방식은 `DataPersistence` PoC에서 검증한 패턴을 따르되, 코드/DB 파일을 직접 공유하지 않는 독립 repo이다.
