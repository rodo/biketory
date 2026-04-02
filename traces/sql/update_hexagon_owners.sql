UPDATE traces_hexagon h
SET owner_id        = sub.user_id,
    owner_points    = sub.points,
    owner_claimed_at = sub.last_earned_at
FROM (
    SELECT DISTINCT ON (hs.hexagon_id)
           hs.hexagon_id, hs.user_id, hs.points, hs.last_earned_at
    FROM traces_hexagonscore hs
    WHERE hs.hexagon_id IN (
        SELECT h2.id FROM traces_hexagon h2
        WHERE ST_Within(h2.geom, ST_SetSRID(%s::geometry, 4326))
    )
    AND hs.points > 0
    ORDER BY hs.hexagon_id, hs.points DESC, hs.last_earned_at DESC
) sub
WHERE h.id = sub.hexagon_id
