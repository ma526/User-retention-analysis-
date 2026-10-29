"""
SQL pipeline on SQLite (no Spark needed). Runs sql/01..08 in order; each file is one SELECT that is
materialised as a table named after the file (01_events_aged.sql -> events_aged) and exported to CSV.

    python src/run_sql_pipeline.py --data data --out outputs/tables
"""
import argparse, glob, os, re, sqlite3, time
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--sql", default="sql")
    ap.add_argument("--out", default="outputs/tables")
    ap.add_argument("--db", default="data/events.db")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if os.path.exists(args.db):
        os.remove(args.db)

    con = sqlite3.connect(args.db)
    t0 = time.time()
    for name in ("users", "events"):
        for chunk in pd.read_csv(os.path.join(args.data, f"{name}.csv"), chunksize=500_000):
            chunk.to_sql(name, con, if_exists="append", index=False)
    con.execute("CREATE INDEX ix_events_user ON events(user_id)")
    con.execute("CREATE INDEX ix_users_user ON users(user_id)")
    print(f"loaded CSVs in {time.time()-t0:.0f}s")

    for path in sorted(glob.glob(os.path.join(args.sql, "*.sql"))):
        name = re.sub(r"^\d+_", "", os.path.splitext(os.path.basename(path))[0])
        query = open(path).read().strip().rstrip(";")
        t = time.time()
        con.execute(f"DROP TABLE IF EXISTS {name}")
        con.execute(f"CREATE TABLE {name} AS {query}")
        if name == "events_aged":
            con.execute("CREATE INDEX ix_aged_user ON events_aged(user_id)")
        df = pd.read_sql(f"SELECT * FROM {name}", con)
        if name not in ("events_aged",):                       # events_aged is too large to export
            df.to_csv(os.path.join(args.out, f"{name}.csv"), index=False)
        print(f"{name:<18} rows={len(df):>9,}  {time.time()-t:.0f}s")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
