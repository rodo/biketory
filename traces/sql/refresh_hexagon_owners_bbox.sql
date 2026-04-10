-- Recalculate owner/owner_points/owner_claimed_at for all hexagons in a bbox.
-- Hexagons with scores get the top scorer; hexagons without scores get NULLed.
-- Parameters: 1-4 = west, south, east, north
WITH bbox_hexagons AS (
    SELECT h.id
    FROM traces_hexagon h
    WHERE h.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
),
top_scorer AS (
    SELECT DISTINCT ON (hs.hexagon_id)
           hs.hexagon_id, hs.user_id, hs.points, hs.last_earned_at
    FROM traces_hexagonscore hs
    WHERE hs.hexagon_id IN (SELECT id FROM bbox_hexagons)
      AND hs.points > 0
    ORDER BY hs.hexagon_id, hs.points DESC, hs.last_earned_at DESC
)
UPDATE traces_hexagon h
SET owner_id         = ts.user_id,
    owner_points     = ts.points,
    owner_claimed_at = ts.last_earned_at
FROM bbox_hexagons bh
LEFT JOIN top_scorer ts ON ts.hexagon_id = bh.id
WHERE h.id = bh.id
  AND (h.owner_id IS DISTINCT FROM ts.user_id
       OR h.owner_points IS DISTINCT FROM ts.points)
