SELECT
    ST_XMin(extent) AS xmin,
    ST_YMin(extent) AS ymin,
    ST_XMax(extent) AS xmax,
    ST_YMax(extent) AS ymax
FROM (
    SELECT ST_Extent(h.geom) AS extent
    FROM traces_hexagon h
    INNER JOIN traces_hexagonscore hs ON hs.hexagon_id = h.id
    WHERE hs.points > 0
) sub
