SELECT date_trunc(%s, uploaded_at) AS period,
       COUNT(*)                     AS traces_uploaded
FROM   traces_trace
GROUP  BY 1
ORDER  BY 1
