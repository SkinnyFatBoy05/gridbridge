select
    feeder_id,
    interval_start_utc,
    sum(energy_kwh) as energy_kwh,
    sum(energy_kwh * 60.0 / interval_minutes) as average_load_kw,
    count(distinct meter_id) as contributing_meters
from {{ ref('stg_meter_intervals') }}
group by feeder_id, interval_start_utc

