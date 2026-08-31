# Client Data Onboarding Questionnaire

Use this before requesting an extract. It is designed to surface ownership, grain and operational constraints early.

## Business outcome and scope

1. Which operational decision will this data support, and who approves the result?
2. Which network area, customer population, asset classes and date range are in scope?
3. What is the required first-value date, refresh cadence and acceptable data latency?
4. Which outputs are advisory, which are operational, and which must never trigger automation?

## Source ownership and access

1. Who owns each meter, GIS, SCADA, DER, asset and market source?
2. Who can explain semantics and who can authorize an extract?
3. Is access file-based, API, event stream, database view or vendor-managed export?
4. What authentication, network path, change window and expiry constraints apply?
5. Which environments can contain real identifiers, and may synthetic test extracts be created?

## Contract and grain

1. What is one row or event, and what fields form its stable business key?
2. Are records snapshots, deltas, corrections or append-only events?
3. How are deletions, cancellations, revisions and late arrivals represented?
4. Which fields are mandatory, conditionally mandatory or vendor extensions?
5. What code lists and reference tables define asset types, phases, channels and quality?

## Time series

1. Is the timestamp interval-start, interval-end, event time, receipt time or market time?
2. Is it UTC, local time with offset, local time without offset or fixed AEST market time?
3. How are daylight-saving repeated/nonexistent times encoded?
4. What is the expected cadence, lateness, backfill window and gap policy?
5. Are values instantaneous power, interval energy, cumulative registers or averages?

## Units and engineering semantics

1. Which units are valid per field, and can they vary by device or export?
2. Are signs import/export, generation/load or source-system conventions?
3. Which voltage, capacity, quality and plausibility limits are authoritative?
4. Which topology is expected to be radial, and how are open/de-energized assets represented?

## Quality and acceptance

1. What known gaps, duplicates, orphan assets and unit mismatches already exist?
2. Which defects block the whole run, and which may be quarantined within tolerance?
3. Who owns remediation, and what evidence is needed to accept an exception?
4. What source and target row counts constitute signed-off reconciliation?

## Security and operations

1. What classification applies to customer, premise, asset and operational identifiers?
2. What retention, residency, encryption, audit and deletion obligations apply?
3. Which roles may upload, run, review, replay and administer pipelines?
4. What constitutes an incident, who is notified, and what evidence must be preserved?
5. Which regulatory or assurance frameworks actually apply in the client's jurisdiction?

