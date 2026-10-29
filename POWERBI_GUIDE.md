# Power BI dashboard guide

A `.pbix` file can't be generated outside Power BI Desktop, so this guide gives the exact data model,
measures and page layout. Building it takes about 30-45 minutes.

## 1. Load data (Get Data -> Text/CSV), from `outputs/tables/`
| Table | File | Grain |
|---|---|---|
| user_master | user_master.csv | 1 row per user (attributes, week-1 features, retention flags) |
| cohort_retention | cohort_retention.csv | 1 row per signup week |
| segment_retention | segment_retention.csv | 1 row per dimension/segment |
| feature_adoption | feature_adoption.csv | 1 row per feature |
| daily_activity | daily_activity.csv | 1 row per day |
| behavioral_segments | behavioral_segments.csv | 1 row per KMeans segment |
| churn_scores | churn_scores.csv | 1 row per test-set user (model output) |
| feature_importance | feature_importance.csv | 1 row per model feature |
| model_metrics | model_metrics.csv | 1 row per model |

## 2. Relationships
- `user_master[user_id]` 1 -> 1 `churn_scores[user_id]` (single direction from user_master)
- `churn_scores[segment]` many -> 1 `behavioral_segments[segment]`
- Other tables are standalone aggregates (no relationship needed).

## 3. DAX measures (create in a `_Measures` table)
```DAX
Total Users        = COUNTROWS ( user_master )
D7 Retention %     = AVERAGE ( user_master[retained_d7] )
D30 Retention %    = AVERAGE ( user_master[retained_d30] )
Churn Rate %       = 1 - [D30 Retention %]
Avg Events Week 1  = AVERAGE ( user_master[n_events_w1] )
High-Risk Users    = CALCULATE ( COUNTROWS ( churn_scores ), churn_scores[risk_band] = "High" )
High-Risk Share    = DIVIDE ( [High-Risk Users], COUNTROWS ( churn_scores ) )
Adoption Lift (pp) = AVERAGE ( feature_adoption[d30_retention_adopters] )
                     - AVERAGE ( feature_adoption[d30_retention_non_adopters] )
Actual Churn (scored) = AVERAGE ( churn_scores[churned_30d] )
Avg Predicted Churn   = AVERAGE ( churn_scores[churn_prob] )
```
Format the percentage measures as `0.0%`.

## 4. Pages
1. **Executive overview** - cards: Total Users, D7 Retention %, D30 Retention %, Churn Rate %;
   line chart `daily_activity[dau]` by `event_day`; clustered column of `cohort_retention` d7/d30 by signup_week;
   slicers: role, plan, channel (from user_master).
2. **Retention drivers** - bar charts from `segment_retention` filtered by `dimension`
   (channel, plan, team_size, features_tried_w1). Use a slicer on `dimension` or one visual per dimension.
3. **Feature adoption** - bar: `adoption_rate` by feature; clustered bar: d30 retention adopters vs non-adopters.
   Add a note: "Correlation, not causation - engaged users try more features."
4. **Behavioural segments** - donut of `share_of_users`; bar of `d30_retention` by segment; table of segment profile.
5. **Churn model & risk** - cards from `model_metrics` (ROC-AUC, F1, Recall); bar of `feature_importance`;
   column chart of High/Medium/Low users with `Actual Churn` per band (shows the model is calibrated);
   table of top high-risk users (filter `risk_band = High`, sort by `churn_prob`).

## 5. Design tips
Consistent 4-colour palette, titles that state the insight ("Teammate-invited users retain 18 pp better"),
no more than 6 visuals per page, a tooltip page for segment details.
