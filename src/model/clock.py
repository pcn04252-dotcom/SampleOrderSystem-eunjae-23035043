import datetime as dt
import time


class Clock:
    def now(self) -> dt.datetime:
        raise NotImplementedError


class ScaledSystemClock(Clock):
    """실제 시간에 배율을 곱해 시뮬레이션 시각을 계산하는 Clock.

    scale_seconds_per_minute: 시뮬레이션 1분에 해당하는 실제 초.
    기본값 1.0은 "실제 1초 = 시뮬레이션 1분" 배율을 의미한다.
    """

    def __init__(self, scale_seconds_per_minute: float = 1.0):
        self._scale = scale_seconds_per_minute
        self._start_real = time.monotonic()
        self._start_sim = dt.datetime.now()

    def now(self) -> dt.datetime:
        elapsed_real_seconds = time.monotonic() - self._start_real
        elapsed_sim_minutes = elapsed_real_seconds / self._scale
        return self._start_sim + dt.timedelta(minutes=elapsed_sim_minutes)


class FakeClock(Clock):
    """테스트용 Clock. 임의의 시각으로 즉시 이동할 수 있다."""

    def __init__(self, start: dt.datetime | None = None):
        self._now = start or dt.datetime(2026, 1, 1)

    def now(self) -> dt.datetime:
        return self._now

    def advance(self, **timedelta_kwargs) -> None:
        self._now += dt.timedelta(**timedelta_kwargs)

    def set(self, value: dt.datetime) -> None:
        self._now = value
