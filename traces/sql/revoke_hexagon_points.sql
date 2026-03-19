-- Decrement by 1 the score of each hexagon contained in the given surface polygon,
-- then delete scores that have dropped to zero.
-- Parameters: 1 = surface polygon WKT, 2 = user_id
WITH hexes AS (
    SELECT h.id AS hexagon_id
    FROM traces_hexagon h
    WHERE ST_Within(h.geom, ST_SetSRID(%s::geometry, 4326))
),
decremented AS (
    UPDATE traces_hexagonscore
    SET points = points - 1
    WHERE hexagon_id IN (SELECT hexagon_id FROM hexes)
      AND user_id = %s
    RETURNING hexagon_id, user_id, points
)
DELETE FROM traces_hexagonscore
WHERE (hexagon_id, user_id) IN (
    SELECT hexagon_id, user_id FROM decremented WHERE points <= 0
)
