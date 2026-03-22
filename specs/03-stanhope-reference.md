# Stanhope Reference Spec

## Goal
Script the acquisition and use of the ECCC Stanhope reference station
for comparison and validation tasks.

## Source
External source: ECCC Stanhope station (ID: 8300590)

## Policy
- Download once when needed
- cache locally
- treat cached local copy as canonical for project work
- do not hammer the API or bulk endpoints

## Anti-429 Requirements
The retrieval implementation must:
- use coarse-grained requests where possible
- insert delays between requests
- avoid repeated re-downloads of existing cached files
- support restart/resume behavior
- record provenance of downloaded files

## Cached Outputs
Store:
- raw downloaded reference data
- normalized reference data
- metadata or provenance record

## Provenance Record
Track at minimum:
- source URL or endpoint pattern
- station identifier
- request date/time
- coverage period
- local cache path

## Use Cases
Stanhope data supports:
- benchmarking against park stations
- validating overlap and similarity
- cross-referencing FWI values when possible

## Acceptance Criteria
This spec is satisfied when:
- Stanhope retrieval is scripted
- cached data is used on repeated runs
- retrieval behavior is rate-limit aware
- provenance is recorded and inspectable
