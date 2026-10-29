-- First-week (age 0-6) behaviour per user. ONLY these features feed the churn model (no leakage).
SELECT user_id,
       COUNT(*)                                                    AS n_events_w1,
       COUNT(DISTINCT age_day)                                     AS n_active_days_w1,
       COUNT(DISTINCT feature)                                     AS n_features_w1,
       SUM(CASE WHEN feature = 'Design'      THEN 1 ELSE 0 END)    AS design_w1,
       SUM(CASE WHEN feature = 'FigJam'      THEN 1 ELSE 0 END)    AS figjam_w1,
       SUM(CASE WHEN feature = 'Prototyping' THEN 1 ELSE 0 END)    AS prototyping_w1,
       SUM(CASE WHEN feature = 'Dev Mode'    THEN 1 ELSE 0 END)    AS devmode_w1,
       SUM(CASE WHEN feature = 'Plugins'     THEN 1 ELSE 0 END)    AS plugins_w1,
       SUM(CASE WHEN feature = 'AI'          THEN 1 ELSE 0 END)    AS ai_w1,
       SUM(CASE WHEN feature = 'Collab'      THEN 1 ELSE 0 END)    AS collab_w1,
       SUM(CASE WHEN event_type = 'comment_added'   THEN 1 ELSE 0 END) AS comments_w1,
       SUM(CASE WHEN event_type = 'share_link_sent' THEN 1 ELSE 0 END) AS shares_w1,
       SUM(CASE WHEN age_day = 0 THEN 1 ELSE 0 END)                AS day0_events,
       MAX(age_day)                                                AS last_active_day_w1
FROM events_aged
WHERE age_day BETWEEN 0 AND 6
GROUP BY user_id
