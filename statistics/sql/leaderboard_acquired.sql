SELECT user_id, COUNT(*) AS acquired
FROM traces_hexagonscore
WHERE points > 0
GROUP BY user_id
