select
    cast(region as varchar) as region,
    cast(interval_start_utc as timestamptz) as interval_start_utc,
    cast(revision as integer) as revision,
    cast(price_aud_per_mwh as double) as price_aud_per_mwh,
    cast(intervention as boolean) as intervention,
    cast(_run_id as varchar) as run_id
from {{ source('gridbridge', 'market_prices') }}
qualify row_number() over (
    partition by region, interval_start_utc order by revision desc
) = 1

