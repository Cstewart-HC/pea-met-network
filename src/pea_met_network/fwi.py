"""Canadian Fire Weather Index moisture-code helpers."""

from __future__ import annotations

import math


def fine_fuel_moisture_code(
    temp: float,
    rh: float,
    wind: float,
    rain: float,
    ffmc0: float,
) -> float:
    """Return daily FFMC from previous day's FFMC and weather inputs."""
    ffmc_coefficient = 250.0 * 59.5 / 101.0
    mo = ffmc_coefficient * (101.0 - ffmc0) / (59.5 + ffmc0)

    if rain > 0.5:
        rf = rain - 0.5
        delta_mrf = (
            42.5
            * rf
            * math.exp(-100.0 / (251.0 - mo))
            * (1.0 - math.exp(-6.93 / rf))
        )
        mr = mo + delta_mrf
        if mo > 150.0:
            mr += 0.0015 * (mo - 150.0) * (mo - 150.0) * math.sqrt(rf)
        mo = min(mr, 250.0)

    ed = (
        0.942 * (rh**0.679)
        + 11.0 * math.exp((rh - 100.0) / 10.0)
        + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
    )
    ew = (
        0.618 * (rh**0.753)
        + 10.0 * math.exp((rh - 100.0) / 10.0)
        + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
    )

    if mo < ed and mo < ew:
        k0w = 0.424 * (1.0 - ((100.0 - rh) / 100.0) ** 1.7)
        k0w += 0.0694 * math.sqrt(wind) * (
            1.0 - ((100.0 - rh) / 100.0) ** 8
        )
        kw = k0w * 0.581 * math.exp(0.0365 * temp)
        m = ew - (ew - mo) / (10.0**kw)
    elif mo > ed:
        k0d = 0.424 * (1.0 - (rh / 100.0) ** 1.7)
        k0d += 0.0694 * math.sqrt(wind) * (1.0 - (rh / 100.0) ** 8)
        kd = k0d * 0.581 * math.exp(0.0365 * temp)
        m = ed + (mo - ed) / (10.0**kd)
    else:
        m = mo

    m = min(max(m, 0.0), 250.0)
    ffmc = 59.5 * (250.0 - m) / (ffmc_coefficient + m)
    return min(max(ffmc, 0.0), 101.0)
