WITH owned AS (
    SELECT h.owner_id AS user_id, h.geom,
           ST_ClusterDBSCAN(h.geom, eps := 0.0001, minpoints := 1)
             OVER (PARTITION BY h.owner_id) AS cluster_id
    FROM traces_hexagon h
    WHERE h.owner_id IS NOT NULL
),
cluster_stats AS (
    SELECT user_id, cluster_id,
           COUNT(*) AS hex_count,
           ST_Area(ST_Union(geom)::geography) AS area_m2,
           ST_Union(geom) AS cluster_geom
    FROM owned
    GROUP BY user_id, cluster_id
),
best_per_user AS (
    SELECT DISTINCT ON (user_id)
           user_id, hex_count, area_m2, cluster_geom
    FROM cluster_stats
    ORDER BY user_id, hex_count DESC, area_m2 DESC
)
SELECT user_id, hex_count, area_m2, cluster_geom
FROM best_per_user
ORDER BY hex_count DESC, area_m2 DESC
