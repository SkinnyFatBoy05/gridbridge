select feeder_id, interval_start_utc
from {{ ref('int_feeder_interval_load') }}
group by feeder_id, interval_start_utc
having count(*) > 1
