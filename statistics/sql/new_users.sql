SELECT date_trunc(%s, date_joined)::date AS period,
       COUNT(*)                           AS new_users
FROM   auth_user
WHERE  date_joined >= %s::date
  AND  date_joined <  (%s::date + interval '1 day')
GROUP  BY 1
