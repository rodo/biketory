SELECT
    h.id,
    ST_AsText(h.geom) AS geom_wkt,
    hs.points
FROM traces_hexagon h
INNER JOIN traces_hexagonscore hs ON hs.hexagon_id = h.id
WHERE h.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
  AND hs.user_id = %s AND hs.points > 0
