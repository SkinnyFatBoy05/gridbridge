select
    load.feeder_id,
    load.interval_start_utc,
    load.energy_kwh,
    load.average_load_kw,
    load.contributing_meters,
    coalesce(der.eligible_der_kw, 0.0) as eligible_der_kw,
    price.region,
    price.price_aud_per_mwh,
    price.intervention
from {{ ref('int_feeder_interval_load') }} as load
left join {{ ref('int_der_capacity') }} as der using (feeder_id)
inner join {{ ref('stg_market_prices') }} as price using (interval_start_utc)
