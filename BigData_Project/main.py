#!/usr/bin/env python3
"""
NYC Taxi EV Charging Station Analysis
======================================
Big Data Course Final Project

Research Question:
  "How can a Spark-based big data pipeline analyze NYC taxi trip data to
   identify high-traffic zones where EV charging stations are needed most
   to reduce urban carbon emissions?"

Team Members:
  • Ankith Reddy Kasani
  • Ayush Manchanda

Usage:
  python main.py [--num-records N] [--num-clusters K] [--run-scalability]
                 [--data-path /path/to/data.csv]
"""

import argparse
import logging
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

# ── make src/ importable regardless of working directory ──────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import Config
from data_generator import generate_synthetic_data
from data_pipeline import DataPipeline
from ml_models import MLModels
from ev_recommender import EVRecommender
from visualizer import Visualizer
from scalability import ScalabilityAnalyzer

# ── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Spark session factory ──────────────────────────────────────────────────

def create_spark(config: Config):
    """
    Build a SparkSession with sensible defaults for both local and
    cluster (Databricks / EMR) environments.
    """
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder
        .appName("NYC_Taxi_EV_Charging_Analysis")
        .config("spark.sql.adaptive.enabled",                 "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.driver.memory",                        config.SPARK_DRIVER_MEMORY)
        .config("spark.executor.memory",                      config.SPARK_EXECUTOR_MEMORY)
        .config("spark.sql.shuffle.partitions",               config.SPARK_SHUFFLE_PARTS)
        .config("spark.serializer",
                "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
    )

    # On Databricks the session already exists; on local, create it.
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


# ── helpers ────────────────────────────────────────────────────────────────

def _banner():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║  NYC TAXI EV CHARGING STATION ANALYSIS                         ║")
    print("║  Spark-Based Big Data Pipeline                                  ║")
    print("║  Team: Ankith Reddy Kasani  •  Ayush Manchanda                 ║")
    print("╚" + "═" * 68 + "╝")
    print()


def _step(msg: str) -> None:
    logger.info("━━━ %s ━━━", msg)


# ── main pipeline ──────────────────────────────────────────────────────────

def main(args) -> None:
    _banner()
    config     = Config(args)
    wall_start = time.perf_counter()

    # ── 1. Spark session ──────────────────────────────────────────────────
    _step("Initialising Apache Spark")
    spark = create_spark(config)
    logger.info("Spark %s  •  Python %s", spark.version, sys.version.split()[0])

    # ── 2. Data ingestion ─────────────────────────────────────────────────
    _step("Data Ingestion")
    if not os.path.exists(config.RAW_DATA_PATH):
        logger.info(
            "No raw data found — generating %d synthetic NYC taxi trips …",
            config.SYNTHETIC_RECORDS,
        )
        generate_synthetic_data(config.RAW_DATA_PATH, config.SYNTHETIC_RECORDS)

    pipeline = DataPipeline(spark, config)
    df_raw   = pipeline.load_data()
    raw_count = df_raw.count()
    logger.info("Raw records loaded: %d", raw_count)

    # ── 3. ETL — clean & feature engineering ─────────────────────────────
    _step("ETL — Cleaning & Feature Engineering")
    df_features = pipeline.clean_and_engineer(df_raw)
    df_features.cache()
    clean_count = df_features.count()
    logger.info(
        "Clean records: %d  (%.1f%% retained)",
        clean_count, 100 * clean_count / raw_count,
    )
    pipeline.save_processed(df_features)

    # ── 4. Zone-level aggregation ─────────────────────────────────────────
    _step("Zone-Level Aggregation")
    df_zones   = pipeline.build_zone_aggregates(df_features)
    df_hourly  = pipeline.build_hourly_demand(df_features)
    df_zones.cache()
    df_hourly.cache()
    logger.info("Unique pickup zones: %d", df_zones.count())
    pipeline.save_zone_aggregates(df_zones)

    # ── 5. KMeans clustering ──────────────────────────────────────────────
    _step("KMeans Clustering (k=%d)" % config.NUM_CLUSTERS)
    ml = MLModels(spark, config)
    df_clustered, kmeans_model, cluster_summary = ml.run_kmeans(df_zones)
    df_clustered.cache()
    logger.info("Cluster summary:\n%s",
                cluster_summary[["cluster", "num_zones",
                                  "total_trips", "rush_hour_fraction",
                                  "dominant_borough"]].to_string(index=False))

    # Elbow curve (k=2..9) — skip for large datasets to save time
    if clean_count <= 200_000:
        _step("KMeans Elbow Analysis")
        elbow = ml.find_optimal_k(df_zones, k_range=range(2, 10))
    else:
        elbow = None

    # ── 6. Demand prediction regression ──────────────────────────────────
    _step("Demand Prediction — Regression Models")
    regression_results = ml.run_regression(df_hourly)
    for model_key in ["linear_regression", "gbt"]:
        r = regression_results[model_key]
        logger.info(
            "%-25s  RMSE=%.3f  MAE=%.3f  R²=%.4f",
            r["model"], r["rmse"], r["mae"], r["r2"],
        )

    # ── 7. EV charging recommendations ───────────────────────────────────
    _step("EV Charging Station Recommendation Engine")
    recommender    = EVRecommender(config)
    recommendations = recommender.generate_recommendations(
        df_clustered, cluster_summary
    )

    # ── 8. Visualisations ────────────────────────────────────────────────
    _step("Generating Visualisations")
    viz = Visualizer(config)
    viz.generate_all(
        df_features, df_clustered,
        cluster_summary, recommendations,
        regression_results,
    )
    if elbow:
        from visualizer import plot_elbow_curve
        plot_elbow_curve(elbow, config.CHARTS_DIR)

    # ── 9. Scalability analysis (optional) ────────────────────────────────
    if args.run_scalability:
        _step("Scalability Analysis")
        analyzer = ScalabilityAnalyzer(spark, config)
        analyzer.run_analysis()

    # ── 10. Final summary ─────────────────────────────────────────────────
    wall_time = time.perf_counter() - wall_start
    df_features.unpersist()
    df_zones.unpersist()
    df_hourly.unpersist()
    df_clustered.unpersist()

    print()
    print("╔" + "═" * 68 + "╗")
    print("║  PIPELINE COMPLETE                                              ║")
    print(f"║  Total wall-clock time : {wall_time:>6.1f} s                            ║")
    print(f"║  Raw records processed : {raw_count:>10,}                       ║")
    print(f"║  Clean records         : {clean_count:>10,}                       ║")
    print(f"║  Clusters identified   : {config.NUM_CLUSTERS:>6}                            ║")
    print(f"║  EV sites recommended  : {len(recommendations):>6}                            ║")
    print(f"║  Outputs directory     : {config.OUTPUT_DIR:<40} ║")
    print("╚" + "═" * 68 + "╝")
    print()

    spark.stop()


# ── entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NYC Taxi EV Charging Station Analysis — Spark Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--num-records", type=int, default=100_000, metavar="N",
        help="Number of synthetic taxi records to generate (if no CSV provided)",
    )
    parser.add_argument(
        "--num-clusters", type=int, default=8, metavar="K",
        help="Number of KMeans clusters",
    )
    parser.add_argument(
        "--run-scalability", action="store_true",
        help="Run the scalability analysis (adds ~5 minutes)",
    )
    parser.add_argument(
        "--data-path", type=str, default=None, metavar="PATH",
        help="Path to an existing NYC TLC taxi CSV or Parquet file",
    )
    main(parser.parse_args())
