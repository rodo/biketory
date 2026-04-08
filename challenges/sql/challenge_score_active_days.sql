-- Score for active_days challenges.
-- Counts distinct days where the participant uploaded a trace during the challenge period.
-- Parameters: start_date, end_date, challenge_id
SELECT
    cp.user_id,
    COUNT(DISTINCT DATE(t.first_point_date)) AS score
FROM challenges_challengeparticipant cp
JOIN traces_trace t
    ON t.uploaded_by_id = cp.user_id
   AND t.first_point_date >= %s
   AND t.first_point_date <= %s
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
