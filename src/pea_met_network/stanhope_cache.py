from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

STANHOPE_STATION_ID = "8300590"
STANHOPE_CLIMATE_ID = "1108299"
STANHOPE_WEATHERCAN_STATION_ID = 6545
REQUEST_DELAY_SECONDS = 1.0
RAW_CACHE_DIR = Path("data/raw/eccc/stanhope")
PROVENANCE_FILENAME = "provenance.json"


class StanhopeIngestionError(RuntimeError):
    pass


@dataclass(frozen=True)
class StanhopeRequest:
    year: int
    month: int
    interval: str = "hourly"

    def cache_filename(self) -> str:
        return f"stanhope_{self.interval}_{self.year}_{self.month:02d}.csv"

    def coverage_period(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class ProvenanceRecord:
    station_identifier: str
    climate_identifier: str
    interval: str
    year: int
    month: int
    coverage_period: str
    source_url: str
    retrieved_at_utc: str
    local_cache_path: str
    status: str


class StanhopeClient:
    def fetch(self, url: str) -> bytes:
        with urlopen(url) as response:  # noqa: S310
            return response.read()


def build_hourly_url(request: StanhopeRequest) -> str:
    if request.interval != "hourly":
        raise StanhopeIngestionError(
            f"Unsupported interval for URL builder: {request.interval}"
        )

    return (
        "https://climate.weather.gc.ca/climate_data/bulk_data_e.html?"
        f"format=csv&stationID={STANHOPE_WEATHERCAN_STATION_ID}"
        f"&Year={request.year}&Month={request.month}"
        "&Day=1&timeframe=1&submit=Download+Data"
    )


def _provenance_path(cache_dir: Path) -> Path:
    return cache_dir / PROVENANCE_FILENAME


def _load_provenance(cache_dir: Path) -> list[dict[str, object]]:
    path = _provenance_path(cache_dir)
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _save_provenance(cache_dir: Path, records: list[dict[str, object]]) -> None:
    path = _provenance_path(cache_dir)
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")


def fetch_stanhope_hourly_month(
    year: int,
    month: int,
    *,
    cache_dir: Path = RAW_CACHE_DIR,
    client: StanhopeClient | None = None,
    sleep_seconds: float = REQUEST_DELAY_SECONDS,
    force: bool = False,
) -> tuple[Path, str]:
    request = StanhopeRequest(year=year, month=month)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / request.cache_filename()

    if cache_path.exists() and not force:
        return cache_path, "cached"

    source_url = build_hourly_url(request)
    active_client = client or StanhopeClient()

    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    try:
        payload = active_client.fetch(source_url)
    except HTTPError as exc:
        if exc.code == 429:
            raise StanhopeIngestionError(
                "Stanhope retrieval hit HTTP 429; keep cache and retry later."
            ) from exc
        raise StanhopeIngestionError(
            f"Stanhope retrieval failed with HTTP {exc.code}."
        ) from exc

    cache_path.write_bytes(payload)
    record = ProvenanceRecord(
        station_identifier=STANHOPE_STATION_ID,
        climate_identifier=STANHOPE_CLIMATE_ID,
        interval=request.interval,
        year=year,
        month=month,
        coverage_period=request.coverage_period(),
        source_url=source_url,
        retrieved_at_utc=datetime.now(UTC).isoformat(),
        local_cache_path=str(cache_path),
        status="downloaded",
    )
    records = _load_provenance(cache_dir)
    records.append(asdict(record))
    _save_provenance(cache_dir, records)
    return cache_path, "downloaded"
