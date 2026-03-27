WITH affected AS (
    INSERT INTO traces_hexagonscore (hexagon_id, user_id, points, last_earned_at)
    SELECT h.id, %s, 1, %s
    FROM traces_hexagon h
    WHERE ST_Within(h.geom, ST_SetSRID(%s::geometry, 4326))
    ON CONFLICT (hexagon_id, user_id)
    DO UPDATE SET points = traces_hexagonscore.points + 1,
                  last_earned_at = EXCLUDED.last_earned_at
    RETURNING hexagon_id, user_id, last_earned_at, (xmax = 0) AS is_new
)
INSERT INTO traces_hexagongainevent (hexagon_id, user_id, earned_at, is_first)
SELECT hexagon_id, user_id, last_earned_at, is_new FROM affected
