-- Stats for the shared profile page.
-- Params: user_id
SELECT
    u.username,
    COUNT(DISTINCT t.id)  AS traces_count,
    COUNT(DISTINCT hs.hexagon_id) AS hexagons_count,
    COALESCE(SUM(hs.points), 0) AS total_points
FROM auth_user u
LEFT JOIN traces_trace t
    ON t.uploaded_by_id = u.id
LEFT JOIN traces_hexagonscore hs
    ON hs.user_id = u.id
WHERE u.id = %s
GROUP BY u.id, u.username;
