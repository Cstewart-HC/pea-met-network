# Implementation Plan

> **This document is a human-readable mirror.** Authoritative task state,
> gates, and ordering live in `docs/ralph-state.json`. If they disagree,
> the JSON wins.

## Phase Roadmap

| Phase | Name | Status |
|---|---|---|
| 1 | Obtain | done |
| 2 | Scrub | done |
| 3 | Explore | not started |
| 4 | Model: Reference + FWI | in progress |
| 5 | Model: Redundancy | not started |
| 6 | Interpret | not started |

## Current Phase: 4 -- Model: Reference + FWI

### Task Queue

Each task has a **gate** defined in ralph-state.json -- a command the loop
must run to verify completion. The loop may NOT mark a task done unless
its gate exits 0.

#### Completed

- [x] add Stanhope hourly cache fetch scaffolding with local reuse
- [x] record Stanhope download provenance for cached files
- [x] encode anti-429 behavior with coarse monthly fetches and delay hooks
- [x] script bounded multi-month or multi-year Stanhope cache materialization
- [x] produce first cleaned hourly and daily datasets
- [x] prove real-file normalization-to-resampling path on canonical CSV
- [x] add bounded canonical CSV normalization loader
- [x] expose first-class hourly and daily resampling helpers

#### Pending

- [ ] normalize cached Stanhope hourly data into project reference schema
- [ ] define FWI-ready cleaned daily contract
- [ ] implement FFMC moisture code
- [ ] implement DMC moisture code
- [ ] implement DC moisture code
- [ ] implement full FWI chain
- [ ] validate FWI against external reference values

## Carried-Forward Decisions

- use OSEMN as project framing, not as a software framework
- bias toward assignment compliance with sane internal structure
- use both PCA and clustering for redundancy analysis
- implement full FWI chain if data supports it
- treat local cached data as canonical
- enforce hard line length 80, style target 50
- enforce McCabe hard cap 15, target less than 10
- native Python FWI implementation remains the target approach

## Blockers

None currently.
