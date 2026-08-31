select
    feeder_id,
    sum(nameplate_kw) as nameplate_kw,
    sum(least(nameplate_kw, export_limit_kw)) as eligible_der_kw,
    count(*) as der_units
from {{ ref('stg_der_units') }}
group by feeder_id

