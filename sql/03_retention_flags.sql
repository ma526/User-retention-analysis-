-- Retention labels (bracket retention = "came back after the first week"):
--   retained_d7  : any activity on days 7-13  (returned in week 2)
--   retained_d30 : any activity on days 7-29  (still active through the first month)
SELECT user_id,
       MAX(CASE WHEN age_day BETWEEN 7 AND 13 THEN 1 ELSE 0 END) AS retained_d7,
       MAX(CASE WHEN age_day BETWEEN 7 AND 29 THEN 1 ELSE 0 END) AS retained_d30
FROM events_aged
GROUP BY user_id
