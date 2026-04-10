UPDATE challenges_challengeparticipant cp
SET score = cp.score - sub.cnt
FROM (
    SELECT challenge_id, user_id, COUNT(*) AS cnt
    FROM challenges_challengedatasetscore
    WHERE trace_id = %s
    GROUP BY challenge_id, user_id
) sub
WHERE cp.challenge_id = sub.challenge_id
  AND cp.user_id = sub.user_id
