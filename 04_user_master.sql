-- One row per user: attributes + first-week features + retention labels (modelling / Power BI table)
SELECT u.user_id, u.team_id, u.team_size, u.role, u.plan, u.channel, u.platform,
       u.signup_day, u.signup_week,
       f.n_events_w1, f.n_active_days_w1, f.n_features_w1,
       f.design_w1, f.figjam_w1, f.prototyping_w1, f.devmode_w1, f.plugins_w1, f.ai_w1, f.collab_w1,
       f.comments_w1, f.shares_w1, f.day0_events, f.last_active_day_w1,
       r.retained_d7, r.retained_d30
FROM users u
JOIN user_features   f ON u.user_id = f.user_id
JOIN retention_flags r ON u.user_id = r.user_id
