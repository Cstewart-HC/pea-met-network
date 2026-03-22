"""Reference moisture-code vectors derived from gagreene/cffdrs."""

from __future__ import annotations

import pytest

FFMC_VECTORS = [
    pytest.param(
        85.0,
        {"temp": 17.0, "rh": 42.0, "wind": 25.0, "rain": 0.0},
        87.6493555020996,
        id="ffmc-drying-baseline",
    ),
    pytest.param(
        85.0,
        {"temp": 6.0, "rh": 90.0, "wind": 15.0, "rain": 0.6},
        79.39974896674352,
        id="ffmc-light-rain-wetting",
    ),
    pytest.param(
        92.0,
        {"temp": 28.0, "rh": 18.0, "wind": 35.0, "rain": 1.2},
        93.97717349811505,
        id="ffmc-hot-windy-recovery",
    ),
]

DMC_VECTORS = [
    pytest.param(
        6.0,
        {"temp": 17.0, "rh": 42.0, "rain": 0.0, "month": 4, "lat": 46.4},
        8.545051136,
        id="dmc-spring-drying",
    ),
    pytest.param(
        20.0,
        {"temp": 10.0, "rh": 80.0, "rain": 12.0, "month": 10, "lat": 46.4},
        9.674116769007487,
        id="dmc-heavy-rain-reset",
    ),
    pytest.param(
        40.0,
        {"temp": 28.0, "rh": 25.0, "rain": 0.4, "month": 7, "lat": 46.4},
        45.1257322,
        id="dmc-summer-drying",
    ),
]

DC_VECTORS = [
    pytest.param(
        15.0,
        {"temp": 17.0, "rain": 0.0, "month": 4, "lat": 46.4},
        19.014,
        id="dc-spring-drying",
    ),
    pytest.param(
        250.0,
        {"temp": 22.0, "rain": 10.0, "month": 8, "lat": 46.4},
        231.91135794039346,
        id="dc-heavy-rain-recharge",
    ),
    pytest.param(
        80.0,
        {"temp": -3.0, "rain": 0.0, "month": 1, "lat": 46.4},
        79.164,
        id="dc-winter-limited-drying",
    ),
]


@pytest.mark.parametrize(("previous_code", "weather", "expected"), FFMC_VECTORS)
def test_ffmc_vectors_exist(
    previous_code: float,
    weather: dict[str, float],
    expected: float,
) -> None:
    assert previous_code >= 0.0
    assert set(weather) == {"temp", "rh", "wind", "rain"}
    assert expected >= 0.0


@pytest.mark.parametrize(("previous_code", "weather", "expected"), DMC_VECTORS)
def test_dmc_vectors_exist(
    previous_code: float,
    weather: dict[str, float],
    expected: float,
) -> None:
    assert previous_code >= 0.0
    assert set(weather) == {"temp", "rh", "rain", "month", "lat"}
    assert expected >= 0.0


@pytest.mark.parametrize(("previous_code", "weather", "expected"), DC_VECTORS)
def test_dc_vectors_exist(
    previous_code: float,
    weather: dict[str, float],
    expected: float,
) -> None:
    assert previous_code >= 0.0
    assert set(weather) == {"temp", "rain", "month", "lat"}
    assert expected >= 0.0
