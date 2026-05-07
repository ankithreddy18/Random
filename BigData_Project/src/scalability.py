"""
Scalability analysis module.

Measures Spark pipeline runtime at four data-volume levels and compares
against an equivalent single-threaded Pandas implementation to illustrate
the benefit of distributed computing.
"""

import logging
import os
import time
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pyspark.sql import SparkSession

from config import Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pandas baseline implementation (for comparison)
# ---------------------------------------------------------------------------

def _pandas_pipeline(csv_path: str) -> float:
    """Run a simplified Pandas version of the pipeline; return elapsed time."""
    t0 = time.perf_counter()
    df = pd.read_csv(csv_path)

    # Simulate the same operations as Spark pipeline
    df = df.dropna(subset=["trip_distance", "fare_amount",
                             "passenger_count", "PULocationID"])
    df = df[(df["trip_distance"].between(0.1, 100)) &
            (df["fare_amount"].between(2.5, 500)) &
            (df["passenger_count"].between(1, 8))]

    df["tpep_pickup_datetime"]  = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    df["pickup_hour"]    = df["tpep_pickup_datetime"].dt.hour
    df["pickup_dow"]     = df["tpep_pickup_datetime"].dt.dayofweek
    df["is_weekend"]     = df["pickup_dow"].isin([5, 6]).astype(int)
    df["is_rush_hour"]   = (
        df["pickup_hour"].between(7, 9) | df["pickup_hour"].between(16, 19)
    ).astype(int)
    df["trip_duration_min"] = (
        (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"])
        .dt.total_seconds() / 60
    )

    zone_agg = (
        df.groupby("PULocationID")
        .agg(
            total_trips     =("trip_distance", "count"),
            avg_distance    =("trip_distance", "mean"),
            avg_fare        =("fare_amount",   "mean"),
            rush_hour_trips =("is_rush_hour",  "sum"),
        )
        .reset_index()
    )
    zone_agg["rush_hour_fraction"] = (
        zone_agg["rush_hour_trips"] / zone_agg["total_trips"]
    )
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Spark pipeline timing
# ---------------------------------------------------------------------------

def _spark_pipeline(spark: SparkSession, csv_path: str) -> float:
    """Run the core Spark ETL and return elapsed time."""
    from pyspark.sql import functions as F
    from pyspark.sql.types import DoubleType

    t0 = time.perf_counter()

    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(csv_path)
    )

    df = (
        df.dropna(subset=["trip_distance", "fare_amount",
                           "passenger_count", "PULocationID"])
          .filter(F.col("trip_distance").between(0.1, 100))
          .filter(F.col("fare_amount").between(2.5, 500))
          .filter(F.col("passenger_count").between(1, 8))
          .withColumn("pickup_hour",  F.hour("tpep_pickup_datetime"))
          .withColumn("pickup_dow",   F.dayofweek("tpep_pickup_datetime"))
          .withColumn("is_weekend",
                      F.when(F.col("pickup_dow").isin(1, 7), 1).otherwise(0))
          .withColumn("is_rush_hour",
                      F.when(
                          (F.col("pickup_hour").between(7, 9)) |
                          (F.col("pickup_hour").between(16, 19)), 1
                      ).otherwise(0))
          .withColumn("trip_duration_min",
                      (F.col("tpep_dropoff_datetime").cast("long") -
                       F.col("tpep_pickup_datetime").cast("long")) / 60.0)
    )

    zone_agg = (
        df.groupBy("PULocationID")
        .agg(
            F.count("*")                          .alias("total_trips"),
            F.avg("trip_distance")                .alias("avg_distance"),
            F.avg("fare_amount")                  .alias("avg_fare"),
            (F.sum("is_rush_hour") / F.count("*")).alias("rush_hour_fraction"),
        )
    )
    # Force evaluation (Spark is lazy until an action is called)
    zone_agg.count()

    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class ScalabilityAnalyzer:

    def __init__(self, spark: SparkSession, config: Config):
        self.spark  = spark
        self.config = config

    def run_analysis(self) -> dict:
        """
        For each target size, generate a synthetic CSV, time both pipelines,
        and produce a comparison chart + JSON report.
        """
        sizes   = self.config.SCALABILITY_SIZES
        results = {
            "sizes":         [],
            "spark_times":   [],
            "pandas_times":  [],
        }

        sample_dir = self.config.SAMPLE_DATA_DIR
        os.makedirs(sample_dir, exist_ok=True)

        for n in sizes:
            csv_path = os.path.join(sample_dir, f"sample_{n}.csv")
            logger.info("Scalability test — %d records …", n)

            if not os.path.exists(csv_path):
                from data_generator import generate_synthetic_data
                generate_synthetic_data(csv_path, num_records=n, seed=7)

            spark_time  = _spark_pipeline(self.spark, csv_path)
            pandas_time = _pandas_pipeline(csv_path)

            results["sizes"].append(n)
            results["spark_times"].append(round(spark_time, 2))
            results["pandas_times"].append(round(pandas_time, 2))

            logger.info(
                "  n=%d  Spark=%.2fs  Pandas=%.2fs",
                n, spark_time, pandas_time,
            )

        self._save_results(results)
        self._plot(results)
        return results

    def _save_results(self, results: dict) -> None:
        path = os.path.join(self.config.RESULTS_DIR, "scalability_results.json")
        with open(path, "w") as fh:
            json.dump(results, fh, indent=2)
        logger.info("Scalability results saved → %s", path)

    def _plot(self, results: dict) -> None:
        sizes       = results["sizes"]
        spark_t     = results["spark_times"]
        pandas_t    = results["pandas_times"]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # ---- absolute runtime
        ax1.plot(sizes, spark_t,  "o-", color="#e63946", linewidth=2.5,
                 markersize=8, label="Apache Spark")
        ax1.plot(sizes, pandas_t, "s--", color="#457b9d", linewidth=2.5,
                 markersize=8, label="Pandas (single-threaded)")
        ax1.set_xlabel("Dataset Size (rows)", fontsize=12)
        ax1.set_ylabel("Processing Time (seconds)", fontsize=12)
        ax1.set_title("Absolute Processing Time vs Dataset Size",
                      fontsize=13, fontweight="bold")
        ax1.legend(fontsize=11)
        ax1.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
        ax1.grid(alpha=0.4)

        # ---- speedup ratio
        speedup = [p / s if s > 0 else 1.0
                   for p, s in zip(pandas_t, spark_t)]
        ax2.plot(sizes, speedup, "D-", color="#2ca02c", linewidth=2.5,
                 markersize=8)
        ax2.axhline(1.0, linestyle="--", color="#888", linewidth=1.5,
                    label="Break-even (speedup = 1×)")
        ax2.set_xlabel("Dataset Size (rows)", fontsize=12)
        ax2.set_ylabel("Speedup (Pandas time / Spark time)", fontsize=12)
        ax2.set_title("Spark Speedup over Pandas",
                      fontsize=13, fontweight="bold")
        ax2.legend(fontsize=11)
        ax2.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
        ax2.grid(alpha=0.4)

        fig.suptitle(
            "Scalability Analysis — Apache Spark vs Pandas\n"
            "(Single-node; speedup advantage grows at production scale)",
            fontsize=14, fontweight="bold",
        )
        fig.tight_layout()

        path = os.path.join(self.config.CHARTS_DIR, "11_scalability_analysis.png")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.info("Scalability chart saved → %s", path)

        # Print summary table
        print("\n" + "=" * 55)
        print("  SCALABILITY ANALYSIS RESULTS")
        print("=" * 55)
        print(f"  {'Records':>10}  {'Spark (s)':>10}  {'Pandas (s)':>10}  {'Speedup':>8}")
        print("-" * 55)
        for n, st, pt, su in zip(sizes, spark_t, pandas_t, speedup):
            print(f"  {n:>10,}  {st:>10.2f}  {pt:>10.2f}  {su:>7.2f}×")
        print("=" * 55 + "\n")
