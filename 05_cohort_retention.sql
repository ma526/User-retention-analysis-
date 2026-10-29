-- Weekly signup cohorts: 7-day and 30-day retention
SELECT signup_week,
       COUNT(*)                   AS cohort_size,
       AVG(retained_d7  * 1.0)    AS d7_retention,
       AVG(retained_d30 * 1.0)    AS d30_retention
FROM user_master
GROUP BY signup_week
ORDER BY signup_week
