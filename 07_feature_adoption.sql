-- Week-1 feature adoption and 30-day retention of adopters vs non-adopters.
-- Only users who signed up on/after day 20 are compared, so every feature (incl. AI,
-- launched day 20) was available for their entire first week.
WITH eligible AS (
    SELECT user_id, retained_d30 FROM user_master WHERE signup_day >= 20
),
tot AS (
    SELECT COUNT(*) AS n, SUM(retained_d30) AS r FROM eligible
),
adopt AS (
    SELECT a.feature, COUNT(*) AS adopters, SUM(el.retained_d30) AS adopter_ret
    FROM (SELECT DISTINCT user_id, feature FROM events_aged WHERE age_day BETWEEN 0 AND 6) a
    JOIN eligible el ON a.user_id = el.user_id
    GROUP BY a.feature
)
SELECT adopt.feature,
       adopt.adopters,
       adopt.adopters * 1.0 / tot.n                              AS adoption_rate,
       adopt.adopter_ret * 1.0 / adopt.adopters                  AS d30_retention_adopters,
       (tot.r - adopt.adopter_ret) * 1.0 / (tot.n - adopt.adopters) AS d30_retention_non_adopters
FROM adopt CROSS JOIN tot
ORDER BY adoption_rate DESC
