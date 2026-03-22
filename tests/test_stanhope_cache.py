from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

import pytest

from pea_met_network.stanhope_cache import (
    STANHOPE_CLIMATE_ID,
    STANHOPE_STATION_ID,
    StanhopeClient,
    StanhopeIngestionError,
    StanhopeRequest,
    build_hourly_url,
    fetch_stanhope_hourly_month,
)


class FakeClient(StanhopeClient):
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        return self.payload


class RateLimitedClient(StanhopeClient):
    def fetch(self, url: str) -> bytes:
        raise HTTPError(url, 429, "too many requests", hdrs=None, fp=None)


def test_build_hourly_url_uses_expected_station_and_month() -> None:
    url = build_hourly_url(StanhopeRequest(year=2024, month=3))

    assert "stationID=6545" in url
    assert "Year=2024" in url
    assert "Month=3" in url
    assert "timeframe=1" in url


def test_fetch_stanhope_hourly_month_downloads_and_records_provenance(
    tmp_path: Path,
) -> None:
    client = FakeClient(b"col1,col2\n1,2\n")

    cache_path, status = fetch_stanhope_hourly_month(
        2024,
        3,
        cache_dir=tmp_path,
        client=client,
        sleep_seconds=0,
    )

    provenance_path = tmp_path / "provenance.json"

    assert status == "downloaded"
    assert cache_path.exists()
    assert cache_path.read_text() == "col1,col2\n1,2\n"
    assert len(client.calls) == 1
    assert provenance_path.exists()

    provenance = provenance_path.read_text()
    assert STANHOPE_STATION_ID in provenance
    assert STANHOPE_CLIMATE_ID in provenance
    assert "2024-03" in provenance
    assert str(cache_path) in provenance


def test_fetch_stanhope_hourly_month_reuses_existing_cache(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "stanhope_hourly_2024_03.csv"
    cache_path.write_text("cached\n")
    client = FakeClient(b"new\n")

    resolved_path, status = fetch_stanhope_hourly_month(
        2024,
        3,
        cache_dir=tmp_path,
        client=client,
        sleep_seconds=0,
    )

    assert status == "cached"
    assert resolved_path == cache_path
    assert resolved_path.read_text() == "cached\n"
    assert client.calls == []


def test_fetch_stanhope_hourly_month_raises_clean_error_on_429(
    tmp_path: Path,
) -> None:
    with pytest.raises(StanhopeIngestionError, match="HTTP 429"):
        fetch_stanhope_hourly_month(
            2024,
            3,
            cache_dir=tmp_path,
            client=RateLimitedClient(),
            sleep_seconds=0,
        )

    assert not (tmp_path / "stanhope_hourly_2024_03.csv").exists()
    assert not (tmp_path / "provenance.json").exists()
