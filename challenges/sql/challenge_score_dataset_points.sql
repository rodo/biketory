-- Score for dataset_points challenges.
-- Reads the pre-computed score from ChallengeParticipant (maintained by trigger).
-- Parameters: challenge_id
SELECT
    cp.user_id,
    cp.score
FROM challenges_challengeparticipant cp
WHERE cp.challenge_id = %s
  AND cp.score > 0
