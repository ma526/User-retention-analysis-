-- Retention by user attribute and by simple week-1 behaviour buckets
SELECT 'role' AS dimension, role AS segment, COUNT(*) AS users,
       AVG(retained_d7 * 1.0) AS d7_retention, AVG(retained_d30 * 1.0) AS d30_retention
FROM user_master GROUP BY role
UNION ALL
SELECT 'plan', plan, COUNT(*), AVG(retained_d7 * 1.0), AVG(retained_d30 * 1.0)
FROM user_master GROUP BY plan
UNION ALL
SELECT 'channel', channel, COUNT(*), AVG(retained_d7 * 1.0), AVG(retained_d30 * 1.0)
FROM user_master GROUP BY channel
UNION ALL
SELECT 'platform', platform, COUNT(*), AVG(retained_d7 * 1.0), AVG(retained_d30 * 1.0)
FROM user_master GROUP BY platform
UNION ALL
SELECT 'team_size',
       CASE WHEN team_size = 1 THEN '1 (solo)' WHEN team_size <= 5 THEN '3-5'
            WHEN team_size <= 10 THEN '10' ELSE '25' END AS segment,
       COUNT(*), AVG(retained_d7 * 1.0), AVG(retained_d30 * 1.0)
FROM user_master
GROUP BY CASE WHEN team_size = 1 THEN '1 (solo)' WHEN team_size <= 5 THEN '3-5'
              WHEN team_size <= 10 THEN '10' ELSE '25' END
UNION ALL
SELECT 'features_tried_w1',
       CASE WHEN n_features_w1 <= 1 THEN '1' WHEN n_features_w1 = 2 THEN '2'
            WHEN n_features_w1 = 3 THEN '3' ELSE '4+' END AS segment,
       COUNT(*), AVG(retained_d7 * 1.0), AVG(retained_d30 * 1.0)
FROM user_master
GROUP BY CASE WHEN n_features_w1 <= 1 THEN '1' WHEN n_features_w1 = 2 THEN '2'
              WHEN n_features_w1 = 3 THEN '3' ELSE '4+' END
