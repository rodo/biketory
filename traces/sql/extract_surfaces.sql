WITH source AS (
    SELECT
        id AS trace_id,
        route AS geom
    FROM traces_trace
    WHERE id = %s
),

noded AS (
    SELECT
        trace_id,
        ST_Node(ST_UnaryUnion(geom)) AS geom
    FROM source
),

polygonized AS (
    SELECT
        trace_id,
        ST_Polygonize(geom) AS geom_collection
    FROM noded
    GROUP BY trace_id
),

dumped AS (
    SELECT
        trace_id,
        (ST_Dump(geom_collection)).path[1] AS polygon_index,
        (ST_Dump(geom_collection)).geom    AS polygon
    FROM polygonized
),

repaired AS (
    SELECT
        trace_id,
        polygon_index,
        CASE
            WHEN ST_IsValid(polygon) THEN polygon
            ELSE ST_MakeValid(polygon)
        END AS polygon
    FROM dumped
)

SELECT
    trace_id,
    polygon_index,
    polygon,
    ST_Area(polygon::geography)        AS area_m2,
    ST_Area(polygon::geography) / 1e6  AS area_km2,
    ST_Centroid(polygon)               AS centroid,
    ST_Perimeter(polygon::geography)   AS perimeter_m
FROM repaired
WHERE ST_IsValid(polygon)
  AND ST_Area(polygon) > 0
ORDER BY polygon_index
