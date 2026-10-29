# User-retention-analysis-
# AI Feature Adoption & User Retention Analysis

End-to-end product analytics project : **2.7M simulated user
events**, SQL / PySpark feature pipeline, cohort retention, behavioural segmentation, churn prediction
(Logistic Regression + XGBoost) and a Power BI dashboard
> (see `src/simulate_events.py`): collaboration and team context drive retention, feature preferences
> Findings show the *methodology and pipeline*,
> not discoveries about real users.

## Business questions
1. Which features do new users adopt in week 1, and does adoption relate to retention?
2. How do 7-day and 30-day retention differ across signup cohorts and user segments?
3. Which behaviours in the first week signal that a user will churn?
4. Can we flag at-risk users early enough for product / lifecycle teams to act?

## Pipeline
```
simulate_events.py  ->  data/events.csv (2.7M rows), data/users.csv (250K users)
        |
sql/01..08 (run via SQLite  OR  PySpark)  ->  outputs/tables/*.csv
        |
train_models.py  ->  segments, LR vs XGBoost, feature importance, churn scores, figures
        |
Power BI (powerbi/POWERBI_GUIDE.md)  ->  5-page dashboard
```

## Definitions (leakage-safe)
- **Week 1** = days 0-6 after signup. **All model features come only from week 1.**
- **7-day retention** = any activity on days 7-13. **30-day retention** = any activity on days 7-29.
- **Churn label** = no activity on days 7-29 (`1 - retained_d30`).
- **Split** = by signup cohort in time: train weeks 0-5, validation week 6, test weeks 7-8. The decision
  threshold is tuned on validation only.

## How to run
```bash
pip install -r requirements.txt
python src/simulate_events.py --events 2700000 --out data
python src/run_sql_pipeline.py            # SQLite, about 1 minute
# or, to demonstrate distributed processing (same SQL files):
python src/run_spark_pipeline.py          # needs pyspark + Java
python src/train_models.py                # needs xgboost for true XGBoost; falls back to sklearn otherwise
```
Then follow `powerbi/POWERBI_GUIDE.md`.

## Results (from the run included in this repo)
**Dataset:** 2,700,000 events, 249,975 users, 40,122 teams, 90 days.

**Retention** (all cohorts, flat across weeks by design): 7-day ~54%, 30-day ~58%.

| Segment | 30-day retention |
|---|---|
| Teammate-invited users | 69.3% |
| Organic / paid users | 51.2% / 52.0% |
| Free vs paid plans | 53.9% vs ~65% |
| Solo users vs 25-person teams | 42.0% vs 62.4% |
| Tried 1 feature in week 1 vs 4+ | 22.5% vs 89.2% |

**Behavioural segments (KMeans, k=4):** Low-touch (37% of users, 27.6% retained), Casual (33%, 69.1%),
Engaged (16%, 74.5%), Power collaborators (13%, 97.7%).

**AI feature (users who signed up after launch):** week-1 adopters retained at 75.0% vs 47.6% for
non-adopters. This is *correlational*: engaged users try more of everything, so don't call it a causal effect.

**Churn models (held-out later cohorts, n = 45,739):**

| Model | ROC-AUC | PR-AUC | F1 | Precision | Recall | Log loss |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.848 | 0.763 | 0.743 | 0.661 | 0.848 | 0.467 |
| Gradient boosting* | 0.849 | 0.764 | 0.744 | 0.656 | 0.857 | 0.466 |


**Key drivers:** first-week event volume dominates (permutation AUC drop ~0.30); acquisition channel, recency,
plan and team size are far smaller. Gradient boosting barely beats Logistic Regression because the simulated
relationships are mostly monotonic; on real data, expect a larger gap.

**Risk bands are calibrated:** predicted Low / Medium / High risk users actually churned at 11.5% / 50.5% / 77.2%.


## Repository layout
```
src/        simulate_events.py, run_sql_pipeline.py, run_spark_pipeline.py, train_models.py
sql/        01_events_aged ... 08_daily_activity (portable SQL: SQLite and Spark SQL)
data/       sample_events_10k.csv (full CSVs are generated locally)
outputs/    tables/ (Power BI inputs, model metrics) and figures/ (PNG charts)
powerbi/    POWERBI_GUIDE.md (data model, DAX, page layout)
```
