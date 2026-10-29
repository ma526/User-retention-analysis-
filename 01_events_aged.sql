-- Attach each event's "age" = days since the user's signup (integer math only: runs in SQLite and Spark SQL)
SELECT e.event_id, e.user_id, e.event_day, e.event_type, e.feature,
       e.event_day - u.signup_day AS age_day
FROM events e
JOIN users u ON e.user_id = u.user_id
