# Redundancy Analysis Spec

## Goal
Assess whether any weather stations are redundant using more than one
analytical view, while remaining assignment compliant.

## Required Methods
Use both:
- PCA
- clustering

PCA alone is not sufficient for a redundancy recommendation.

## Benchmarking Requirement
Statistically compare park stations against the ECCC Stanhope reference
station to quantify similarity where overlap allows.

## Analytical Expectations
The analysis should include, where supported by the data:
- correlation or similarity structure
- variance overlap
- clustering behavior among stations
- time-series comparisons
- distance or similarity summaries relative to Stanhope

## Recommendation Principle
Do not recommend removing a station based on a single metric.
A removal or retention recommendation must synthesize:
- PCA evidence
- clustering evidence
- reference benchmarking
- uncertainty analysis
- any known data quality caveats

## Acceptance Criteria
This spec is satisfied when:
- PCA outputs exist and are interpretable
- clustering outputs exist and are interpretable
- benchmarking to Stanhope is documented
- station redundancy recommendations are evidence-based and qualified
