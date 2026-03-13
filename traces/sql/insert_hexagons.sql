INSERT INTO traces_hexagon (geom, created_at)
SELECT ST_Transform(ST_SetSRID(geom, 3857), 4326), NOW()
FROM ST_HexagonGrid(%s, ST_Transform(ST_SetSRID(%s::geometry, 4326), 3857))
ON CONFLICT (geom) DO NOTHING
