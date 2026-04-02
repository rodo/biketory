SELECT user_id, SUM(points) AS total_points
FROM traces_hexagonscore
WHERE points > 0
GROUP BY user_id
