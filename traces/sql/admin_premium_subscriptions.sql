SELECT date_trunc(%s, created_at) AS period,
       COUNT(*)                    AS new_subscriptions
FROM   traces_subscription
GROUP  BY 1
ORDER  BY 1
