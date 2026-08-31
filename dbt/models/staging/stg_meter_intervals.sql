select
    cast(meter_id as varchar) as meter_id,
    cast(channel as varchar) as channel,
    cast(feeder_id as varchar) as feeder_id,
    cast(interval_start_utc as timestamptz) as interval_start_utc,
    cast(interval_minutes as integer) as interval_minutes,
    cast(energy_kwh as double) as energy_kwh,
    cast(_run_id as varchar) as run_id
from {{ source('gridbridge', 'meter_intervals') }}

