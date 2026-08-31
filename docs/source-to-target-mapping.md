# Source-to-Target Mapping

## Mapping rules

Mappings are versioned in `config/source_mappings.yml`. Unknown required fields, units or ambiguous times are rejected rather than coerced.

### Meter intervals → `meter_intervals`

| Source field | Canonical field | Transformation | Exception |
|---|---|---|---|
| `meter_id` | `meter_id` | Trimmed source identifier | Missing identifier fails contract |
| `nmi` | `nmi` | Preserved; redacted in operator logs | Missing value can be quarantined by client rule |
| `connection_point_id` | `connection_point_id` | Direct mapping | Unknown connection is a relationship exception |
| `feeder_id` | `feeder_id` | Direct mapping | Missing feeder fails dbt not-null test |
| `channel` | `channel` | Direct mapping | Part of natural key |
| `interval_start_local` | `interval_start_utc` | IANA-zone parse, explicit DST handling, convert to UTC | Ambiguous naive time → `TIMESTAMP_DST_AMBIGUOUS` |
| `energy_value` + `energy_unit` | `energy_kwh` | Wh × 0.001, kWh × 1, MWh × 1000 | Unsupported unit → `UNIT_UNSUPPORTED` |

Natural key: `(meter_id, channel, interval_start_utc)`.

### GIS GeoJSON → `network_assets`

| Source field | Canonical field | Transformation | Exception |
|---|---|---|---|
| `properties.asset_id` | `asset_id` | Direct mapping | Duplicate asset updates by payload fingerprint |
| `properties.asset_type` | `asset_type` | Controlled type | Unsupported type stays outside graph checks |
| `properties.from_node` / `to_node` | same | Direct mapping | Missing referenced node → `GIS_DANGLING_NODE` |
| `properties.nominal_voltage_v` | `nominal_voltage_v` | Numeric volts | Non-positive → `GIS_INVALID_VOLTAGE` |
| `geometry` | `geometry_json` | Canonical compact JSON | Missing → `GIS_MISSING_GEOMETRY` |

Natural key: `(asset_id)`.

### SCADA NDJSON → `scada_observations`

| Source field | Canonical field | Transformation | Exception |
|---|---|---|---|
| `point_id` | `point_id` | Direct mapping | Required |
| `asset_id` | `asset_id` | Direct mapping | Unknown asset → `SCADA_UNKNOWN_ASSET` in production evolution |
| `event_time` | `event_time_utc` | ISO parse and UTC conversion | Invalid timestamp fails contract |
| `value` + `unit` | `power_kw` | W/kW/MW normalization | Unsupported unit → `UNIT_UNSUPPORTED` |
| `quality_code` | `quality_code` | `GOOD` accepted | Other value → `SCADA_BAD_QUALITY` |
| `sequence_number` | `sequence_number` | Integer | Repeated point/sequence → `SCADA_DUPLICATE_SEQUENCE` |

Natural key: `(point_id, event_time_utc, sequence_number)`.

### DER CSV → `der_units`

| Source field | Canonical field | Transformation | Exception |
|---|---|---|---|
| `der_id` | `der_id` | Direct mapping | Duplicate → `DER_DUPLICATE` |
| `connection_point_id` | `connection_point_id` | Direct mapping | Unknown point → `DER_UNKNOWN_CONNECTION` in production evolution |
| `feeder_id` | `feeder_id` | Direct mapping | Required for capacity aggregation |
| `nameplate_value` + `nameplate_unit` | `nameplate_kw` | W/kW/MW normalization | Unsupported unit → `DER_UNIT_UNSUPPORTED` |
| `export_limit_kw` | `export_limit_kw` | Numeric kW | Above nameplate → `DER_EXPORT_ABOVE_NAMEPLATE` |

Natural key: `(der_id)`.

### Market JSON → `market_prices`

| Source field | Canonical field | Transformation | Exception |
|---|---|---|---|
| `region` | `region` | NEM region code | Unknown region → `MARKET_INVALID_REGION` |
| `interval_start` | `interval_start_utc` | ISO parse and UTC conversion | Invalid timestamp fails contract |
| `price_aud_per_mwh` | same | Numeric A$/MWh | Preserved, including valid negative prices |
| `revision` | `revision` | Integer; dbt selects latest | Duplicate region/interval/revision → `MARKET_DUPLICATE_INTERVAL` |

Natural key: `(region, interval_start_utc, revision)`.

