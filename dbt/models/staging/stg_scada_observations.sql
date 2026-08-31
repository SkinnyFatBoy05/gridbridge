select
    cast(point_id as varchar) as point_id,
    cast(asset_id as varchar) as asset_id,
    cast(event_time_utc as timestamptz) as event_time_utc,
    cast(sequence_number as bigint) as sequence_number,
    cast(quality_code as varchar) as quality_code,
    cast(power_kw as double) as power_kw,
    cast(_run_id as varchar) as run_id
from {{ source('gridbridge', 'scada_observations') }}

