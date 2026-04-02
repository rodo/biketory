-- 3 most recently active friends (latest trace per friend).
-- Params: user_id (twice, once per UNION branch).
SELECT u.id, u.username, u.first_name,
       t.uploaded_at, t.uuid AS trace_uuid
FROM auth_user u
INNER JOIN (
    SELECT f.from_user_id AS friend_id FROM traces_friendship f
    WHERE f.to_user_id = %s AND f.status = 'accepted'
    UNION
    SELECT f.to_user_id FROM traces_friendship f
    WHERE f.from_user_id = %s AND f.status = 'accepted'
) friends ON friends.friend_id = u.id
INNER JOIN LATERAL (
    SELECT t2.uploaded_at, t2.uuid
    FROM traces_trace t2
    WHERE t2.uploaded_by_id = u.id
    ORDER BY t2.uploaded_at DESC
    LIMIT 1
) t ON true
ORDER BY t.uploaded_at DESC
LIMIT 3
