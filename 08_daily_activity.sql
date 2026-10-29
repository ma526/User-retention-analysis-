-- Daily active users and event volume (engagement trend)
SELECT event_day, COUNT(DISTINCT user_id) AS dau, COUNT(*) AS events
FROM events
GROUP BY event_day
ORDER BY event_day
