# Data-Quality Reason-Code Catalogue

| Code | Gate | Operator action |
|---|---|---|
| `METER_DUPLICATE_INTERVAL` | Quarantine later duplicate | Confirm revision semantics; replay corrected extract |
| `METER_NEGATIVE_IMPORT` | Quarantine | Confirm channel/sign convention or map export separately |
| `METER_UNKNOWN` | Quarantine | Add authoritative meter relationship before replay |
| `TIMESTAMP_DST_AMBIGUOUS` | Quarantine | Supply explicit UTC offset or UTC timestamp |
| `UNIT_UNSUPPORTED` | Quarantine | Add source-owned unit definition and tested mapping |
| `GIS_DANGLING_NODE` | Topology invalid; flex blocked | Supply missing node or correct edge reference |
| `GIS_MISSING_GEOMETRY` | Quarantine | Provide valid GeoJSON geometry |
| `GIS_INVALID_VOLTAGE` | Quarantine | Confirm nominal-voltage unit/value |
| `SCADA_BAD_QUALITY` | Quarantine; excluded from operations | Resolve quality flag at source or await good observation |
| `SCADA_DUPLICATE_SEQUENCE` | Quarantine duplicate | Confirm event ordering and replay contract |
| `SCADA_IMPLAUSIBLE_VALUE` | Quarantine | Confirm unit, scaling and sensor state |
| `SCADA_UNKNOWN_ASSET` | Relationship exception | Map point to authoritative asset |
| `DER_DUPLICATE` | Quarantine duplicate | Confirm registration revision/current record |
| `DER_UNIT_UNSUPPORTED` | Quarantine | Supply W, kW or MW semantics; never infer MVA→kW |
| `DER_UNKNOWN_CONNECTION` | Relationship exception | Resolve connection point before eligibility |
| `DER_EXPORT_ABOVE_NAMEPLATE` | Quarantine | Correct export/nameplate fields or document exception |
| `MARKET_DUPLICATE_INTERVAL` | Quarantine identical revision | Confirm revision ordering |
| `MARKET_INVALID_REGION` | Quarantine | Map to an accepted NEM region code |

Quarantine is evidence, not deletion. A replay references its parent run and uses the original source hash or a corrected source object so the resolution remains auditable.

