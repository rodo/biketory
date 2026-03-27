SELECT
    periods.period,
    COALESCE(u.new_users, 0)          AS new_users,
    COALESCE(t.traces_uploaded, 0)    AS traces_uploaded,
    COALESCE(t.total_distance_km, 0)  AS total_distance_km,
    COALESCE(cs.surfaces_detected, 0) AS surfaces_detected,
    COALESCE(hge.hexagons_earned, 0)  AS hexagons_earned
FROM generate_series(%s::date, %s::date, ('1 ' || %s)::interval) AS periods(period)
LEFT JOIN (
    SELECT date_trunc(%s, date_joined)::date AS period,
           COUNT(*) AS new_users
    FROM   auth_user
    GROUP  BY 1
) u ON u.period = periods.period
LEFT JOIN (
    SELECT date_trunc(%s, uploaded_at)::date AS period,
           COUNT(*) AS traces_uploaded,
           COALESCE(SUM(length_km), 0) AS total_distance_km
    FROM   traces_trace
    GROUP  BY 1
) t ON t.period = periods.period
LEFT JOIN (
    SELECT date_trunc(%s, detected_at)::date AS period,
           COUNT(*) AS surfaces_detected
    FROM   traces_closedsurface
    GROUP  BY 1
) cs ON cs.period = periods.period
LEFT JOIN (
    SELECT date_trunc(%s, earned_at)::date AS period,
           COUNT(*) AS hexagons_earned
    FROM   traces_hexagongainevent
    GROUP  BY 1
) hge ON hge.period = periods.period
ORDER BY 1
