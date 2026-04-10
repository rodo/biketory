-- Find dataset features that fall within hexagons acquired by a trace,
-- i.e. hexagons contained in the trace's closed surfaces.
-- Each trace can score a feature once, but different traces can each
-- score the same feature (one point per trace per feature).
-- Parameters: challenge_id, trace_id, challenge_id, user_id, trace_id
SELECT DISTINCT df.id AS dataset_feature_id
FROM traces_closedsurface cs
JOIN traces_hexagon h ON ST_Within(h.geom, cs.polygon)
JOIN challenges_datasetfeature df ON ST_Contains(h.geom, df.geom)
JOIN challenges_challenge c ON c.id = %s AND c.dataset_id = df.dataset_id
WHERE cs.trace_id = %s
  AND NOT EXISTS (
    SELECT 1 FROM challenges_challengedatasetscore cds
    WHERE cds.challenge_id = %s AND cds.user_id = %s
      AND cds.dataset_feature_id = df.id AND cds.trace_id = %s
  )
