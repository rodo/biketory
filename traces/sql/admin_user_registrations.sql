SELECT date_trunc(%s, date_joined) AS period,
       COUNT(*)                     AS new_users
FROM   auth_user
GROUP  BY 1
ORDER  BY 1
