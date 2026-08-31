select meter_id, channel, interval_start_utc
from {{ ref('stg_meter_intervals') }}
group by meter_id, channel, interval_start_utc
having count(*) > 1

