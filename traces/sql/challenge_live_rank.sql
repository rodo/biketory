-- Live rank for a user across multiple challenges.
-- Params: user_id, challenge_ids (array)
SELECT cp.challenge_id,
       1 + COUNT(*) FILTER (WHERE cp2.score > cp.score)
FROM challenges_challengeparticipant cp
JOIN challenges_challengeparticipant cp2
  ON cp2.challenge_id = cp.challenge_id
WHERE cp.user_id = %s
  AND cp.challenge_id = ANY(%s)
GROUP BY cp.challenge_id, cp.score
