import datetime as dt
import time

import pytest

from src.model.clock import Clock, FakeClock, ScaledSystemClock


def test_clock_base_class_now_is_not_implemented():
    with pytest.raises(NotImplementedError):
        Clock().now()


def test_fake_clock_returns_fixed_time_until_advanced():
    clock = FakeClock(start=dt.datetime(2026, 1, 1, 0, 0, 0))
    assert clock.now() == dt.datetime(2026, 1, 1, 0, 0, 0)
    clock.advance(minutes=10)
    assert clock.now() == dt.datetime(2026, 1, 1, 0, 10, 0)


def test_fake_clock_set_jumps_to_arbitrary_time():
    clock = FakeClock()
    target = dt.datetime(2030, 5, 1, 12, 0, 0)
    clock.set(target)
    assert clock.now() == target


def test_scaled_system_clock_advances_with_real_time():
    """mocking 없이 실제 ScaledSystemClock이 실제 시간 경과에 따라 실제로 움직이는지 확인."""
    clock = ScaledSystemClock(scale_seconds_per_minute=1.0)
    t0 = clock.now()
    time.sleep(0.2)
    t1 = clock.now()
    assert t1 > t0
    # 배율 1.0(실제 1초 = 시뮬레이션 1분)이므로 실제 0.2초 경과 시
    # 시뮬레이션상 약 12초(0.2분) 경과해야 한다.
    elapsed_sim_seconds = (t1 - t0).total_seconds()
    assert 8 <= elapsed_sim_seconds <= 16


def test_scaled_system_clock_reflects_configured_scale():
    """배율(scale)이 작을수록 같은 실제 시간에 더 많은 시뮬레이션 시간이 흐르는지 실제로 확인."""
    fast_clock = ScaledSystemClock(scale_seconds_per_minute=0.1)
    t0 = fast_clock.now()
    time.sleep(0.2)
    t1 = fast_clock.now()
    elapsed_sim_minutes = (t1 - t0).total_seconds() / 60
    # 실제 0.2초 / 배율 0.1 = 시뮬레이션 약 2분 경과
    assert 1.5 <= elapsed_sim_minutes <= 3.0
