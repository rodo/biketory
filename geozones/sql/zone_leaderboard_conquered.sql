SELECT hs.user_id, COUNT(*) AS conquered
FROM traces_hexagonscore hs
INNER JOIN (
    SELECT hexagon_id, MAX(points) AS max_points
    FROM traces_hexagonscore
    WHERE points > 0
    GROUP BY hexagon_id
) top ON top.hexagon_id = hs.hexagon_id AND hs.points = top.max_points
INNER JOIN traces_hexagon h ON h.id = hs.hexagon_id
INNER JOIN geozones_geozone gz ON gz.id = %s
WHERE hs.points > 0
  AND ST_Contains(gz.geom, ST_Centroid(h.geom))
GROUP BY hs.user_id
