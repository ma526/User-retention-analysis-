"""
Synthetic Figma-style product event log (default: exactly 2,700,000 events).

IMPORTANT: this data is SIMULATED. Behaviours (collaboration -> retention, role-based
feature preferences, AI rollout on day 20, team effects) are explicit modelling
assumptions, not measurements of real users. Say so in your README / interviews.

Usage:
    python src/simulate_events.py --events 2700000 --out data
Outputs:
    data/events.csv   event_id, user_id, timestamp, event_day, event_type, feature
    data/users.csv    user_id, team_id, team_size, role, plan, channel, platform,
                      signup_day, signup_date, signup_week
"""
import argparse
import os

import numpy as np
import pandas as pd

WINDOW_DAYS = 90        # length of the observation window
SIGNUP_DAYS = 60        # users sign up on days 0..59 (leaves >= 30 days to observe retention)
SIM_DAYS = 35           # days of activity simulated per user (we only need ages 0..29)
AI_LAUNCH_DAY = 20      # AI features become available on this day
START_DATE = pd.Timestamp("2026-01-01")

FEATURES = ["Design", "FigJam", "Prototyping", "Dev Mode", "Plugins", "AI", "Collab"]
EVENT_TYPES = {
    "Design": ["file_created", "file_opened", "component_created"],
    "FigJam": ["board_created", "sticky_added"],
    "Prototyping": ["prototype_created", "prototype_viewed"],
    "Dev Mode": ["inspect_opened", "code_copied"],
    "Plugins": ["plugin_run"],
    "AI": ["ai_layout_generated", "ai_rename_layers"],
    "Collab": ["comment_added", "share_link_sent"],
}
ROLES = ["Designer", "Developer", "PM"]
# relative feature preference per role (order = FEATURES)
ROLE_W = np.array([
    [5.0, 1.0, 3.0, 0.2, 2.0, 1.5, 2.0],   # Designer
    [1.0, 0.5, 0.5, 5.0, 0.8, 1.0, 1.5],   # Developer
    [0.7, 3.0, 1.5, 0.5, 0.3, 1.0, 3.0],   # PM
])


def make_users(n_users, rng):
    """Create teams first so team_size / team effects are consistent."""
    draw = rng.choice([1, 3, 5, 10, 25], size=n_users, p=[.25, .25, .25, .15, .10])
    k = int(np.searchsorted(np.cumsum(draw), n_users)) + 1
    team_idx = np.repeat(np.arange(k), draw[:k])[:n_users]
    team_size = np.bincount(team_idx)[team_idx]
    team_effect = rng.normal(0, 0.5, k)[team_idx]      # shared team-level engagement

    role = rng.choice(ROLES, n_users, p=[.5, .3, .2])
    plan = rng.choice(["Free", "Professional", "Organization"], n_users, p=[.6, .28, .12])
    channel = rng.choice(["organic", "teammate_invite", "paid"], n_users, p=[.4, .4, .2])
    channel = np.where((team_size == 1) & (channel == "teammate_invite"), "organic", channel)
    platform = rng.choice(["web", "desktop", "mobile"], n_users, p=[.55, .4, .05])
    signup_day = rng.integers(0, SIGNUP_DAYS, n_users)

    # latent engagement (never exported): drives activity level and retention
    z = (0.6 * (channel == "teammate_invite") + 0.4 * (plan != "Free")
         + 0.15 * np.log(team_size) + team_effect + rng.normal(0, 1.0, n_users))

    users = pd.DataFrame({
        "user_id": np.arange(1, n_users + 1),
        "team_id": ["T%05d" % (t + 1) for t in team_idx],
        "team_size": team_size, "role": role, "plan": plan,
        "channel": channel, "platform": platform, "signup_day": signup_day,
    })
    return users, z


def simulate_events(users, z, rng, chunk=40_000):
    role_i = users["role"].map({r: i for i, r in enumerate(ROLES)}).to_numpy()
    signup = users["signup_day"].to_numpy()
    # cumulative feature probabilities: [role, ai_available, feature]
    P = np.zeros((3, 2, len(FEATURES)))
    for r in range(3):
        for a in range(2):
            w = ROLE_W[r].copy()
            if a == 0:
                w[FEATURES.index("AI")] = 0.0
            P[r, a] = np.cumsum(w / w.sum())
    type_tbl = np.full((len(FEATURES), 3), "", dtype=object)
    n_types = np.zeros(len(FEATURES), dtype=int)
    for i, f in enumerate(FEATURES):
        n_types[i] = len(EVENT_TYPES[f])
        type_tbl[i, :n_types[i]] = EVENT_TYPES[f]

    d = np.arange(SIM_DAYS)
    out_u, out_day, out_f, out_t, out_prot = [], [], [], [], []
    for s in range(0, len(users), chunk):
        sl = slice(s, s + chunk)
        zz, sg = z[sl], signup[sl]
        base = np.exp(-0.35 + 0.55 * zz)[:, None]
        decay = np.clip(0.30 - 0.10 * zz, 0.05, 0.9)[:, None]
        day = sg[:, None] + d[None, :]
        lam = base * np.exp(-decay * d[None, :]) * np.where((day % 7) >= 5, 0.6, 1.0)
        cnt = rng.poisson(lam)
        cnt[:, 0] = np.maximum(cnt[:, 0], 1)            # everyone is active on day 0
        cnt = cnt * (day < WINDOW_DAYS)
        ui, di = np.nonzero(cnt)
        rep = cnt[ui, di]
        u_loc = np.repeat(ui, rep)
        dd = np.repeat(di, rep)
        ev_day = sg[u_loc] + dd
        r = role_i[sl][u_loc]
        a = (ev_day >= AI_LAUNCH_DAY).astype(int)
        feat = (rng.random(len(u_loc))[:, None] > P[r, a]).sum(1)
        feat = np.minimum(feat, len(FEATURES) - 1)
        tix = np.minimum((rng.random(len(u_loc)) * n_types[feat]).astype(int), n_types[feat] - 1)
        out_u.append(u_loc + s); out_day.append(ev_day.astype(np.int16))
        out_f.append(feat.astype(np.int8)); out_t.append(type_tbl[feat, tix]); out_prot.append(dd == 0)
    return (np.concatenate(out_u), np.concatenate(out_day), np.concatenate(out_f),
            np.concatenate(out_t), np.concatenate(out_prot))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=2_700_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # pilot run to estimate events per user, then size the population
    pu, pz = make_users(20_000, np.random.default_rng(args.seed))
    pilot = simulate_events(pu, pz, np.random.default_rng(args.seed))
    n_users = int(args.events / (len(pilot[0]) / 20_000) * 1.02)

    rng = np.random.default_rng(args.seed + 1)
    users, z = make_users(n_users, rng)
    u_idx, ev_day, feat, etype, prot = simulate_events(users, z, rng)
    assert len(u_idx) >= args.events, "simulated fewer events than requested"
    if len(u_idx) > args.events:                      # trim extras (never a user's first-day events)
        drop = rng.choice(np.flatnonzero(~prot), len(u_idx) - args.events, replace=False)
        keep = np.ones(len(u_idx), bool)
        keep[drop] = False
        u_idx, ev_day, feat, etype = u_idx[keep], ev_day[keep], feat[keep], etype[keep]

    frac = rng.random(len(u_idx))
    order = np.argsort(ev_day + frac, kind="stable")
    ev = pd.DataFrame({
        "event_id": np.arange(1, len(order) + 1),
        "user_id": users["user_id"].to_numpy()[u_idx[order]],
        "timestamp": START_DATE + pd.to_timedelta((ev_day + frac)[order], unit="D"),
        "event_day": ev_day[order].astype(int),
        "event_type": etype[order],
        "feature": np.array(FEATURES)[feat[order]],
    })
    users["signup_date"] = START_DATE + pd.to_timedelta(users["signup_day"], unit="D")
    users["signup_week"] = users["signup_day"] // 7

    ev["timestamp"] = ev["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    users["signup_date"] = users["signup_date"].dt.strftime("%Y-%m-%d")
    ev.to_csv(os.path.join(args.out, "events.csv"), index=False)
    users.to_csv(os.path.join(args.out, "users.csv"), index=False)
    ev.head(10_000).to_csv(os.path.join(args.out, "sample_events_10k.csv"), index=False)
    print(f"users={len(users):,}  events={len(ev):,}  teams={users.team_id.nunique():,}")


if __name__ == "__main__":
    main()
