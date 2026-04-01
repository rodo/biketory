SELECT hs.user_id, COUNT(*) AS conquered
FROM traces_hexagonscore hs
INNER JOIN (
    SELECT hexagon_id, MAX(points) AS max_points
    FROM traces_hexagonscore
    WHERE points > 0
    GROUP BY hexagon_id
) top ON top.hexagon_id = hs.hexagon_id AND hs.points = top.max_points
WHERE hs.points > 0
GROUP BY hs.user_id
