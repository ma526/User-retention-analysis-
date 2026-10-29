"""
Behavioural segmentation + churn prediction.

Target : churned_30d = 1 - retained_d30   (no activity on days 7-29 after signup)
Inputs : ONLY first-week (days 0-6) behaviour + static user attributes  -> no label leakage
Split  : time-based by signup cohort (train weeks 0-5, validation week 6, test weeks 7-8)
Models : Logistic Regression (baseline) and XGBoost
         (falls back to scikit-learn HistGradientBoosting if xgboost is not installed;
          the model name is recorded in outputs/tables/model_metrics.csv)

    python src/train_models.py --tables outputs/tables --figures outputs/figures
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, f1_score,
                             log_loss, precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

COUNT_COLS = ["n_events_w1", "n_active_days_w1", "n_features_w1", "design_w1", "figjam_w1",
              "prototyping_w1", "devmode_w1", "plugins_w1", "ai_w1", "collab_w1",
              "comments_w1", "shares_w1", "day0_events", "last_active_day_w1"]
NUM_COLS = COUNT_COLS + ["team_size"]
CAT_COLS = ["role", "plan", "channel", "platform"]
SEED = 42


def metrics(name, y, p, thr):
    pred = (p >= thr).astype(int)
    return {"model": name, "threshold": round(float(thr), 3),
            "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred),
            "recall": recall_score(y, pred), "f1": f1_score(y, pred),
            "log_loss": log_loss(y, p), "brier": brier_score_loss(y, p)}


def best_f1_threshold(y, p):
    grid = np.linspace(0.1, 0.9, 81)
    return grid[int(np.argmax([f1_score(y, (p >= t).astype(int)) for t in grid]))]


def segment_users(df, tables):
    """KMeans behavioural segments from first-week activity; named by activity level."""
    cols = ["n_events_w1", "n_active_days_w1", "n_features_w1", "collab_w1", "ai_w1", "day0_events"]
    X = StandardScaler().fit_transform(np.log1p(df[cols]))
    km = KMeans(n_clusters=4, n_init=5, random_state=SEED).fit(X)
    df = df.assign(cluster=km.labels_)
    order = df.groupby("cluster")["n_events_w1"].mean().sort_values().index
    names = dict(zip(order, ["Low-touch", "Casual", "Engaged", "Power collaborators"]))
    df["segment"] = df["cluster"].map(names)
    prof = (df.groupby("segment")
              .agg(users=("user_id", "size"), avg_events_w1=("n_events_w1", "mean"),
                   avg_active_days_w1=("n_active_days_w1", "mean"),
                   avg_features_w1=("n_features_w1", "mean"), avg_collab_w1=("collab_w1", "mean"),
                   d7_retention=("retained_d7", "mean"), d30_retention=("retained_d30", "mean"))
              .reset_index().sort_values("avg_events_w1"))
    prof["share_of_users"] = prof["users"] / len(df)
    prof.to_csv(os.path.join(tables, "behavioral_segments.csv"), index=False)
    print(prof.round(3).to_string(index=False))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", default="outputs/tables")
    ap.add_argument("--figures", default="outputs/figures")
    args = ap.parse_args()
    os.makedirs(args.figures, exist_ok=True)

    df = pd.read_csv(os.path.join(args.tables, "user_master.csv"))
    df["churned_30d"] = 1 - df["retained_d30"]
    df = segment_users(df, args.tables)

    train = df[df.signup_week <= 5]
    val = df[df.signup_week == 6]
    test = df[df.signup_week >= 7]
    print(f"\ntrain={len(train):,}  val={len(val):,}  test={len(test):,}  "
          f"churn rate train={train.churned_30d.mean():.3f} test={test.churned_30d.mean():.3f}")

    log = FunctionTransformer(np.log1p, feature_names_out="one-to-one")
    pre_lr = ColumnTransformer([
        ("num", Pipeline([("log", log), ("sc", StandardScaler())]), COUNT_COLS + ["team_size"]),
        ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), CAT_COLS)])
    pre_tree = ColumnTransformer([
        ("num", "passthrough", NUM_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS)])

    lr = Pipeline([("pre", pre_lr), ("clf", LogisticRegression(max_iter=3000, C=1.0))])
    lr.fit(train[NUM_COLS + CAT_COLS], train.churned_30d)

    if HAS_XGB:
        name = "XGBoost"
        Xtr = pre_tree.fit_transform(train[NUM_COLS + CAT_COLS])
        Xva = pre_tree.transform(val[NUM_COLS + CAT_COLS])
        clf = XGBClassifier(n_estimators=600, max_depth=4, learning_rate=0.05, subsample=0.8,
                            colsample_bytree=0.8, eval_metric="logloss",
                            early_stopping_rounds=30, random_state=SEED, n_jobs=-1)
        clf.fit(Xtr, train.churned_30d, eval_set=[(Xva, val.churned_30d)], verbose=False)
        gb = Pipeline([("pre", pre_tree), ("clf", clf)])      # pre already fitted; re-fit is cheap/no-op for clf
        gb.named_steps["pre"].fit(train[NUM_COLS + CAT_COLS])
    else:
        name = "HistGradientBoosting (XGBoost fallback)"
        print("WARNING: xgboost not installed -> using sklearn HistGradientBoosting. "
              "Run `pip install xgboost` and re-run to get true XGBoost results.")
        gb = Pipeline([("pre", pre_tree),
                       ("clf", HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05,
                                                              max_depth=4, early_stopping=True,
                                                              validation_fraction=0.1,
                                                              random_state=SEED))])
        gb.fit(train[NUM_COLS + CAT_COLS], train.churned_30d)

    rows, probs = [], {}
    for mname, model in [("Logistic Regression", lr), (name, gb)]:
        p_val = model.predict_proba(val[NUM_COLS + CAT_COLS])[:, 1]
        thr = best_f1_threshold(val.churned_30d, p_val)          # threshold chosen on validation only
        p_test = model.predict_proba(test[NUM_COLS + CAT_COLS])[:, 1]
        probs[mname] = p_test
        rows.append(metrics(mname, test.churned_30d, p_test, thr))
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(args.tables, "model_metrics.csv"), index=False)
    print("\nTest-set metrics (later signup cohorts):")
    print(res.round(4).to_string(index=False))

    # ---- feature importance (permutation, model-agnostic, on a test sample) ----
    samp = test.sample(min(30_000, len(test)), random_state=SEED)
    pi = permutation_importance(gb, samp[NUM_COLS + CAT_COLS], samp.churned_30d,
                                scoring="roc_auc", n_repeats=3, random_state=SEED, n_jobs=1)
    imp = (pd.DataFrame({"feature": NUM_COLS + CAT_COLS, "auc_drop": pi.importances_mean})
             .sort_values("auc_drop", ascending=False))
    imp.to_csv(os.path.join(args.tables, "feature_importance.csv"), index=False)
    print("\nTop drivers (permutation importance, AUC drop):")
    print(imp.head(8).round(4).to_string(index=False))

    # ---- churn scores for Power BI ----
    best = name
    out = test[["user_id", "signup_week", "role", "plan", "channel", "segment", "n_events_w1",
                "n_features_w1", "collab_w1", "churned_30d"]].copy()
    out["churn_prob"] = probs[best].round(4)
    out["risk_band"] = pd.cut(out.churn_prob, [-0.01, 0.35, 0.65, 1.01], labels=["Low", "Medium", "High"])
    out.to_csv(os.path.join(args.tables, "churn_scores.csv"), index=False)
    band = out.groupby("risk_band", observed=True).agg(users=("user_id", "size"),
                                                       actual_churn_rate=("churned_30d", "mean"))
    band.to_csv(os.path.join(args.tables, "risk_band_calibration.csv"))
    print("\nRisk bands (does predicted risk match reality?):")
    print(band.round(3))

    # ---- figures ----
    plt.figure(figsize=(5.5, 5))
    for mname, p in probs.items():
        fpr, tpr, _ = roc_curve(test.churned_30d, p)
        plt.plot(fpr, tpr, label=f"{mname} (AUC {roc_auc_score(test.churned_30d, p):.3f})")
    plt.plot([0, 1], [0, 1], "k--", lw=1)
    plt.xlabel("False positive rate"); plt.ylabel("True positive rate")
    plt.title("ROC - held-out later signup cohorts"); plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(os.path.join(args.figures, "roc_curves.png"), dpi=150); plt.close()

    top = imp.head(10).iloc[::-1]
    plt.figure(figsize=(6.5, 4.5))
    plt.barh(top.feature, top.auc_drop, color="#5B6CFF")
    plt.xlabel("Drop in ROC-AUC when shuffled"); plt.title("What drives churn predictions")
    plt.tight_layout(); plt.savefig(os.path.join(args.figures, "feature_importance.png"), dpi=150); plt.close()

    coh = pd.read_csv(os.path.join(args.tables, "cohort_retention.csv"))
    plt.figure(figsize=(6.5, 4))
    plt.plot(coh.signup_week, coh.d7_retention * 100, marker="o", label="7-day")
    plt.plot(coh.signup_week, coh.d30_retention * 100, marker="o", label="30-day")
    plt.ylim(0, 100); plt.xlabel("Signup week"); plt.ylabel("Retention %")
    plt.title("Cohort retention by signup week"); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(args.figures, "cohort_retention.png"), dpi=150); plt.close()

    seg = pd.read_csv(os.path.join(args.tables, "behavioral_segments.csv"))
    plt.figure(figsize=(6.5, 4))
    plt.bar(seg.segment, seg.d30_retention * 100, color="#16A085")
    plt.ylabel("30-day retention %"); plt.title("Retention by behavioural segment")
    plt.xticks(rotation=15); plt.tight_layout()
    plt.savefig(os.path.join(args.figures, "segment_retention.png"), dpi=150); plt.close()
    print("\nSaved tables and figures.")


if __name__ == "__main__":
    main()
