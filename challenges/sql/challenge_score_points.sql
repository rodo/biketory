-- Score for max_points challenges.
-- Sums HexagonScore.points earned during the challenge period on challenge hexagons.
-- Parameters: challenge_id, start_date, end_date
SELECT
    cp.user_id,
    COALESCE(SUM(hs.points), 0) AS score
FROM challenges_challengeparticipant cp
JOIN challenges_challengehexagon ch
    ON ch.challenge_id = cp.challenge_id
LEFT JOIN traces_hexagonscore hs
    ON hs.hexagon_id = ch.hexagon_id
   AND hs.user_id = cp.user_id
   AND hs.last_earned_at >= %s
   AND hs.last_earned_at <= %s
WHERE cp.challenge_id = %s
GROUP BY cp.user_id
