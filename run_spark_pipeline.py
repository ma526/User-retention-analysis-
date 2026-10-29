"""
Same pipeline on PySpark: the SAME sql/*.sql files are executed with spark.sql, so results match the
SQLite version. Use this when you want to demonstrate distributed processing.

    pip install pyspark            # needs Java 8/11/17
    python src/run_spark_pipeline.py --data data --out outputs/tables
"""
import argparse, glob, os, re, time
from pyspark.sql import SparkSession


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--sql", default="sql")
    ap.add_argument("--out", default="outputs/tables")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    spark = (SparkSession.builder.appName("figma-retention")
             .config("spark.sql.shuffle.partitions", "16")
             .config("spark.driver.memory", "4g").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    for name in ("users", "events"):
        (spark.read.csv(os.path.join(args.data, f"{name}.csv"), header=True, inferSchema=True)
              .createOrReplaceTempView(name))

    for path in sorted(glob.glob(os.path.join(args.sql, "*.sql"))):
        name = re.sub(r"^\d+_", "", os.path.splitext(os.path.basename(path))[0])
        query = open(path).read().strip().rstrip(";")
        t = time.time()
        df = spark.sql(query).cache()
        df.createOrReplaceTempView(name)
        n = df.count()
        if name != "events_aged":
            df.toPandas().to_csv(os.path.join(args.out, f"{name}.csv"), index=False)
        print(f"{name:<18} rows={n:>9,}  {time.time()-t:.0f}s")
    spark.stop()


if __name__ == "__main__":
    main()
