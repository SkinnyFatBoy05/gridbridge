# Security Control Mapping

## Status and applicability

This is an educational mapping, not a statement of conformity, certification or regulatory applicability. GridBridge has not undergone an ISO/IEC 27001 audit or a NERC CIP assessment. NERC CIP applies within specific North American Bulk Electric System contexts and is not an Australian distribution-utility compliance framework.

The mapping uses the [official ISO/IEC 27001:2022 overview](https://www.iso.org/standard/27001) and [NERC Reliability Standards families](https://www.nerc.com/standards/reliability-standards) only as public orientation sources. Exact applicability and control interpretation require qualified client security, legal and compliance owners.

## Implemented portfolio evidence

| Security objective | GridBridge evidence | Boundary |
|---|---|---|
| Information integrity | SHA-256 source manifests, stable payload fingerprints, exact row reconciliation | Local files and DuckDB only |
| Data minimization | Synthetic fixtures; reports show hashes and counts rather than raw identifiers | No production discovery/classification engine |
| Logging and accountability | Run IDs, parent replay IDs, source manifests, quarantine reason codes, completion status | Local audit store is not tamper-proof WORM storage |
| Secure configuration | Validated YAML thresholds, `.env.example`, no required secrets in demo | Local compose credentials are development-only |
| Change control | Git history, pull-request CI, dbt tests, mapping version and design records | No organization approval workflow |
| Vulnerability hygiene | Pinned lockfile, dependency review, secret scan and container scan in CI | Results depend on GitHub runner/tool availability |
| Fail-closed operation | Reconciliation/dbt failures stop the run; topology/freshness/capacity defects block advice | No operational control plane exists |
| Identifier protection | Stable redaction helper and synthetic-only public fixtures | Raw synthetic payload remains in local landing zone |

## Least-privilege production role design

| Role | Upload source | Run pipeline | View redacted report | View raw/quarantine | Change mappings | Administer platform |
|---|---:|---:|---:|---:|---:|---:|
| Source uploader | Yes | No | Own-source status | No | No | No |
| Pipeline operator | Read landed | Yes | Yes | Time-bound | No | No |
| Data-quality reviewer | No | Request replay | Yes | Approved scope | Propose | No |
| Mapping maintainer | Synthetic samples | Test only | Yes | Approved samples | Pull request | No |
| Security auditor | Metadata | No | Yes | Exceptional approval | No | Read configuration |
| Platform administrator | Infrastructure only | Break-glass | Metadata | Break-glass | Deploy approved | Yes |

## NERC CIP-inspired operational themes

- Security management: explicit ownership, least privilege and configuration evidence.
- System security management: dependency/secret scanning, hardened production images and patch process.
- Incident response: defined stop, preserve, notify and investigate sequence.
- Recovery: versioned mappings, immutable source evidence, idempotent replay and tested restore plan.
- Configuration/change management: reviewed code/config changes and reproducible build evidence.
- Information protection: classification, redaction, retention and controlled raw access.

These themes deliberately avoid claiming that a particular numbered requirement is implemented. A real assessment must use the effective standard and applicability set for the entity and date.

