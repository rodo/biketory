-- Score for visit_hexagons challenges.
-- Counts all hexagons traversed during the challenge period (duplicates included).
-- Parameters: start_date, end_date, challenge_id
SELECT
    cp.user_id,
    COUNT(*) AS score
FROM challenges_challengeparticipant cp
JOIN traces_hexagongainevent e
    ON e.user_id = cp.user_id
   AND e.earned_at >= %s
   AND e.earned_at <= %s
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
