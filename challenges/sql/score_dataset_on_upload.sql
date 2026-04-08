-- Find dataset features that fall within hexagons touched by a trace,
-- excluding features already scored for this user/challenge.
-- Parameters: challenge_id, user_id, trace_route_wkt
SELECT
    df.id AS dataset_feature_id
FROM challenges_datasetfeature df
JOIN challenges_challenge c
    ON c.id = %s
   AND c.dataset_id = df.dataset_id
JOIN traces_hexagon h
    ON ST_Contains(h.geom, df.geom)
WHERE ST_Intersects(
        h.geom,
        ST_SetSRID(ST_GeomFromText(%s), 4326)
      )
  AND NOT EXISTS (
        SELECT 1
        FROM challenges_challengedatasetscore cds
        WHERE cds.challenge_id = %s
          AND cds.user_id = %s
          AND cds.dataset_feature_id = df.id
      )
