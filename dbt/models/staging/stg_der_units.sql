select
    cast(der_id as varchar) as der_id,
    cast(feeder_id as varchar) as feeder_id,
    cast(nameplate_kw as double) as nameplate_kw,
    cast(export_limit_kw as double) as export_limit_kw,
    cast(_run_id as varchar) as run_id
from {{ source('gridbridge', 'der_units') }}

