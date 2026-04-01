SELECT hs.user_id, COUNT(*) AS acquired
FROM traces_hexagonscore hs
INNER JOIN traces_hexagon h ON h.id = hs.hexagon_id
INNER JOIN geozones_geozone gz ON gz.id = %s
WHERE hs.points > 0
  AND ST_Contains(gz.geom, ST_Centroid(h.geom))
GROUP BY hs.user_id
