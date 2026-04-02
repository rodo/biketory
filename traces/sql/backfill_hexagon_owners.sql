UPDATE traces_hexagon h
SET owner_id        = sub.user_id,
    owner_points    = sub.points,
    owner_claimed_at = sub.last_earned_at
FROM (
    SELECT DISTINCT ON (hs.hexagon_id)
           hs.hexagon_id, hs.user_id, hs.points, hs.last_earned_at
    FROM traces_hexagonscore hs
    WHERE hs.points > 0
    ORDER BY hs.hexagon_id, hs.points DESC, hs.last_earned_at DESC
) sub
WHERE h.id = sub.hexagon_id
