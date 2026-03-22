# Implementation Plan

## Current Milestone
Phase 2 — Scrub

## Current Objective
Build the first cleaned-data path on top of the normalized ingestion layer.
The immediate goal is reproducible hourly and daily resampling for station
telemetry using the now-normalized schema families.

## Immediate Next Tasks
- [x] implement hourly resampling on normalized station records
- [x] implement daily resampling on normalized station records
- [x] define aggregation rules per variable family
- [x] add tests for hourly and daily resampling behavior
- [x] write first cleaned output contract for processed data

## Queued Tasks
- [ ] implement imputation audit framework
- [ ] encode conservative missing-data handling rules
- [x] produce first cleaned hourly and daily datasets
- [x] prove real-file normalization-to-resampling path on canonical CSV
- [x] add bounded canonical CSV normalization loader
- [x] expose first-class hourly and daily resampling helpers
- [ ] ingest and cache Stanhope reference data
- [ ] define FWI-ready cleaned daily contract
- [x] validate repo-wide lint and tests before milestone commit

## Validation Expectations
For current scope:
- resampling should be reproducible from normalized inputs
- timestamp buckets should be timezone-stable and UTC-based
- aggregation rules should be explicit and testable
- no silent variable loss during resampling

## Blockers
- none currently

## Recent Decisions
- use OSEMN as project framing, not as a software framework
- bias toward assignment compliance with sane internal structure
- use both PCA and clustering for redundancy analysis
- implement full FWI chain if data supports it
- treat local cached data as canonical
- enforce hard line length 80, style target 50
- enforce McCabe hard cap 15, target less than 10
- diary entries should use factual + reflective Option C style
- manual and scheduled loop runs must be observable by default
- native Python FWI implementation remains the target approach

## Notes to Future Loops
The ingestion groundwork is now real: audit, manifest loading, schema
recognition, and cross-family timestamp normalization exist. Build forward
from that baseline. Do not reopen settled foundation work unless tests or
artifacts prove a real defect.

## Pre-autonomy checkpoint
Completed and verified:
- initial data inventory and schema audit
- planning stack and quality rails
- raw manifest loader and schema recognition
- timestamp normalization for primary schema family
- timestamp normalization across remaining schema families

The next sprint should begin with resampling, not more planning.

## Sprint Update (2026-03-22 05:56:52 UTC)
- Milestone in progress: hourly and daily resampling on normalized station data.
- Sprint mode: 5-loop Ralph-style, one bounded task per loop, observation-first diary updates each loop.
- Current verified start: repo has existing uncommitted work touching plan/docs/src/tests; proceed carefully from working tree as found.
