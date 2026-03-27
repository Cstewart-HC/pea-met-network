# src/pea_met_network/adapters/

## Responsibility
Format adapter layer — routes raw data files (CSV, XLSX, XLE, JSON) through
format-specific loaders that each produce a canonical DataFrame schema.
Implements the Strategy pattern: `BaseAdapter` defines the interface,
concrete adapters implement per-format parsing, and `registry` dispatches
by file extension.

## Design
**Strategy pattern** with a registry-based factory:
- `BaseAdapter` (ABC) — defines the `load(path) → DataFrame` contract
- `CSVAdapter` — PEINP archive CSVs + ECCC Stanhope CSVs (auto-detected by column heuristics)
- `XLSXAdapter` — HOBOware XLSX exports (Greenwich 2023, openpyxl-based)
- `XLEAdapter` — Solinst XLE XML files (Stanley Bridge 2022, defusedxml parser)
- `JSONAdapter` — Licor Cloud API JSON (device-serial-to-station mapping, nested sensor records)
- `column_maps.py` — shared column rename dictionary + prefix extraction logic
- `schema.py` — `CANONICAL_SCHEMA` list defining the target column set
- `registry.py` — `ADAPTER_REGISTRY` dict + `route_by_extension()` factory

## Data Flow
1. `cleaning.py` calls `route_by_extension(file_path)` from `registry.py`
2. Registry maps `.csv` → `CSVAdapter`, `.xlsx` → `XLSXAdapter`, `.xle` → `XLEAdapter`, `.json` → `JSONAdapter`
3. Adapter's `load()` method reads the file, renames columns via `column_maps.rename_columns()`, parses timestamps, and returns a DataFrame
4. All adapters produce DataFrames with at minimum: `station` (str), `timestamp_utc` (datetime64[ns, UTC])
5. Additional canonical columns (`air_temperature_c`, `rain_mm`, etc.) are filled when present in the source

## Module Map

| Module | Responsibility | Key Functions/Classes |
|--------|----------------|----------------------|
| `__init__.py` | Package exports | Re-exports `BaseAdapter`, `route_by_extension`, `ADAPTER_REGISTRY`, `CANONICAL_SCHEMA` |
| `base.py` | Abstract base class | `BaseAdapter.load(path) → DataFrame` |
| `column_maps.py` | Shared column rename mappings | `COLUMN_MAPS`, `SKIP_COLUMNS`, `SKIP_PREFIXES`, `extract_prefix()`, `rename_columns()`, `derive_wind_speed_kmh()` |
| `schema.py` | Canonical schema definition | `CANONICAL_SCHEMA` — list of canonical column names |
| `registry.py` | Extension-to-adapter routing | `ADAPTER_REGISTRY`, `route_by_extension(path) → BaseAdapter` |
| `csv_adapter.py` | CSV loader (PEINP + ECCC) | `CSVAdapter`, `_detect_csv_schema()`, `_load_peinp_csv()`, `_load_eccc_csv()` |
| `xlsx_adapter.py` | XLSX loader (HOBOware) | `XLSXAdapter` |
| `xle_adapter.py` | XLE XML loader (Solinst) | `XLEAdapter` |
| `json_adapter.py` | JSON loader (Licor Cloud) | `JSONAdapter`, `_serial_to_station()`, `_records_to_series()`, `LICOR_MEASUREMENT_MAP` |

## Integration
- **Consumed by**: `cleaning.py` (via `route_by_extension()`)
- **Depends on**: `pandas`, `openpyxl` (xlsx), `defusedxml` (xle), stdlib `json` (json)
- **Column maps shared by**: `csv_adapter.py`, `xlsx_adapter.py` (both use `column_maps.rename_columns()`)
