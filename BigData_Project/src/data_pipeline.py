"""
Spark-based ETL pipeline for NYC Yellow-Taxi trip data.

Stages:
  1. Load  — raw CSV or Parquet
  2. Clean — null removal, range filters, type coercion
  3. Enrich— join zone lookup, derive spatial features
  4. Feats — temporal features, trip-level metrics
  5. Agg   — zone-level aggregation (the "unit" used by ML models)
  6. Save  — write Parquet to disk
"""

import logging
import os

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    IntegerType, StringType, DoubleType, TimestampType,
)

from config import Config, NYC_ZONES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema for raw NYC TLC Yellow-Taxi CSV
# ---------------------------------------------------------------------------
RAW_SCHEMA = StructType([
    StructField("VendorID",              IntegerType(),   True),
    StructField("tpep_pickup_datetime",  TimestampType(), True),
    StructField("tpep_dropoff_datetime", TimestampType(), True),
    StructField("passenger_count",       DoubleType(),    True),
    StructField("trip_distance",         DoubleType(),    True),
    StructField("RatecodeID",            DoubleType(),    True),
    StructField("store_and_fwd_flag",    StringType(),    True),
    StructField("PULocationID",          IntegerType(),   True),
    StructField("DOLocationID",          IntegerType(),   True),
    StructField("payment_type",          IntegerType(),   True),
    StructField("fare_amount",           DoubleType(),    True),
    StructField("extra",                 DoubleType(),    True),
    StructField("mta_tax",               DoubleType(),    True),
    StructField("tip_amount",            DoubleType(),    True),
    StructField("tolls_amount",          DoubleType(),    True),
    StructField("improvement_surcharge", DoubleType(),    True),
    StructField("total_amount",          DoubleType(),    True),
    StructField("congestion_surcharge",  DoubleType(),    True),
])


class DataPipeline:
    """End-to-end Spark ETL pipeline."""

    def __init__(self, spark: SparkSession, config: Config):
        self.spark  = spark
        self.config = config
        self._zone_df = self._build_zone_df()

    # ---------------------------------------------------------------- private

    def _build_zone_df(self) -> DataFrame:
        """Convert the in-memory zone lookup dict to a small Spark DataFrame."""
        rows = [
            (zone_id, info[0], info[1], float(info[2]), float(info[3]))
            for zone_id, info in NYC_ZONES.items()
        ]
        schema = StructType([
            StructField("zone_id",  IntegerType(), False),
            StructField("zone_name",StringType(),  True),
            StructField("borough",  StringType(),  True),
            StructField("zone_lat", DoubleType(),  True),
            StructField("zone_lon", DoubleType(),  True),
        ])
        return self.spark.createDataFrame(rows, schema=schema)

    # ----------------------------------------------------------------- public

    def load_data(self) -> DataFrame:
        """Load raw data from CSV (or Parquet if already converted)."""
        path = self.config.raw_data_path

        # Try Parquet first (faster), fall back to CSV
        parquet_path = path.replace(".csv", ".parquet")
        if os.path.exists(parquet_path):
            logger.info("Loading Parquet: %s", parquet_path)
            return self.spark.read.parquet(parquet_path)

        logger.info("Loading CSV: %s", path)
        # Use inferSchema for timestamps so both whole-second and sub-second
        # formats parse correctly, then cast non-timestamp cols explicitly.
        df = (
            self.spark.read
            .option("header", "true")
            .option("inferSchema", "true")
            .option("timestampFormat", "yyyy-MM-dd HH:mm:ss")
            .csv(path)
        )
        # Ensure critical numeric columns have correct types
        from pyspark.sql.types import IntegerType, DoubleType
        for col_name, dtype in [
            ("VendorID", IntegerType()), ("PULocationID", IntegerType()),
            ("DOLocationID", IntegerType()), ("payment_type", IntegerType()),
            ("passenger_count", DoubleType()), ("trip_distance", DoubleType()),
            ("fare_amount", DoubleType()), ("total_amount", DoubleType()),
            ("RatecodeID", DoubleType()),
        ]:
            if col_name in df.columns:
                df = df.withColumn(col_name, F.col(col_name).cast(dtype))
        return df

    def clean_and_engineer(self, df: DataFrame) -> DataFrame:
        """Full clean + feature-engineering pass."""
        df = self._clean(df)
        df = self._add_temporal_features(df)
        df = self._add_zone_features(df)
        df = self._add_trip_metrics(df)
        return df

    def _clean(self, df: DataFrame) -> DataFrame:
        """Remove nulls, filter invalid values."""
        critical_cols = [
            "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
            "trip_distance", "PULocationID", "DOLocationID",
            "fare_amount", "passenger_count",
        ]
        df = df.dropna(subset=critical_cols)

        df = (
            df
            # Trip distance must be plausible
            .filter(F.col("trip_distance").between(0.1, 100.0))
            # Fare must be plausible
            .filter(F.col("fare_amount").between(2.50, 500.0))
            # Positive passengers
            .filter(F.col("passenger_count").between(1, 8))
            # Dropoff must be after pickup
            .filter(F.col("tpep_dropoff_datetime") > F.col("tpep_pickup_datetime"))
            # Valid zone IDs (NYC TLC uses 1–265)
            .filter(F.col("PULocationID").between(1, 265))
            .filter(F.col("DOLocationID").between(1, 265))
            # No negative fares from data errors
            .filter(F.col("total_amount") > 0)
        )
        return df

    def _add_temporal_features(self, df: DataFrame) -> DataFrame:
        """Extract hour, day-of-week, month, etc. from timestamps."""
        return (
            df
            .withColumn("pickup_hour",       F.hour("tpep_pickup_datetime"))
            .withColumn("pickup_dow",         F.dayofweek("tpep_pickup_datetime"))  # 1=Sun
            .withColumn("pickup_month",       F.month("tpep_pickup_datetime"))
            .withColumn("is_weekend",         F.when(
                                                F.col("pickup_dow").isin(1, 7), 1
                                             ).otherwise(0))
            .withColumn("is_rush_hour",       F.when(
                                                (F.col("pickup_hour").between(7, 9)) |
                                                (F.col("pickup_hour").between(16, 19)), 1
                                             ).otherwise(0))
            .withColumn("time_of_day",        F.when(F.col("pickup_hour").between(0, 5),  "late_night")
                                              .when(F.col("pickup_hour").between(6, 9),   "morning_rush")
                                              .when(F.col("pickup_hour").between(10, 15), "midday")
                                              .when(F.col("pickup_hour").between(16, 19), "evening_rush")
                                              .otherwise("evening"))
        )

    def _add_zone_features(self, df: DataFrame) -> DataFrame:
        """Join pickup/dropoff zone coordinates and borough labels."""
        # Pickup zone
        df = (
            df.join(
                self._zone_df.select(
                    F.col("zone_id").alias("pu_zone_id"),
                    F.col("borough").alias("pu_borough"),
                    F.col("zone_lat").alias("pu_lat"),
                    F.col("zone_lon").alias("pu_lon"),
                ),
                df["PULocationID"] == F.col("pu_zone_id"),
                how="left",
            )
            .drop("pu_zone_id")
        )
        # Dropoff zone
        df = (
            df.join(
                self._zone_df.select(
                    F.col("zone_id").alias("do_zone_id"),
                    F.col("borough").alias("do_borough"),
                ),
                df["DOLocationID"] == F.col("do_zone_id"),
                how="left",
            )
            .drop("do_zone_id")
        )
        return df

    def _add_trip_metrics(self, df: DataFrame) -> DataFrame:
        """Compute trip duration, speed, and cost-per-mile."""
        return (
            df
            .withColumn(
                "trip_duration_min",
                (F.col("tpep_dropoff_datetime").cast("long") -
                 F.col("tpep_pickup_datetime").cast("long")) / 60.0,
            )
            .withColumn(
                "speed_mph",
                F.when(
                    F.col("trip_duration_min") > 0,
                    F.col("trip_distance") / (F.col("trip_duration_min") / 60.0),
                ).otherwise(None),
            )
            .filter(F.col("trip_duration_min").between(1, 300))
            .filter(F.col("speed_mph").between(0.5, 80))
            .withColumn(
                "fare_per_mile",
                F.when(
                    F.col("trip_distance") > 0,
                    F.col("fare_amount") / F.col("trip_distance"),
                ).otherwise(None),
            )
        )

    def build_zone_aggregates(self, df: DataFrame) -> DataFrame:
        """
        Aggregate trip-level data to zone-level features.

        One row per PULocationID — this is the feature matrix fed into KMeans.
        Also creates per-zone-per-hour rows for the demand regression model.
        """
        return (
            df.groupBy("PULocationID")
            .agg(
                F.count("*")                         .alias("total_trips"),
                F.avg("trip_distance")               .alias("avg_distance"),
                F.avg("fare_amount")                 .alias("avg_fare"),
                F.avg("passenger_count")             .alias("avg_passengers"),
                F.avg("trip_duration_min")           .alias("avg_duration_min"),
                F.avg("speed_mph")                   .alias("avg_speed_mph"),
                F.sum("is_rush_hour").cast("double") .alias("rush_hour_trips"),
                F.avg("is_weekend")                  .alias("weekend_fraction"),
                F.first("pu_lat")                    .alias("lat"),
                F.first("pu_lon")                    .alias("lon"),
                F.first("pu_borough")                .alias("borough"),
            )
            .withColumn(
                "rush_hour_fraction",
                F.col("rush_hour_trips") / F.col("total_trips"),
            )
        )

    def build_hourly_demand(self, df: DataFrame) -> DataFrame:
        """
        Aggregate per-zone per-hour trip counts for demand regression.
        """
        return (
            df.groupBy("PULocationID", "pickup_hour", "pickup_dow")
            .agg(
                F.count("*")           .alias("trip_count"),
                F.avg("trip_distance") .alias("avg_distance"),
                F.avg("fare_amount")   .alias("avg_fare"),
                F.first("is_weekend")  .alias("is_weekend"),
                F.first("is_rush_hour").alias("is_rush_hour"),
                F.first("pu_borough")  .alias("borough"),
            )
        )

    def save_processed(self, df: DataFrame) -> None:
        """Write the enriched trip DataFrame to Parquet."""
        path = self.config.processed_data_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.write.mode("overwrite").parquet(path)
        logger.info("Processed data written → %s", path)

    def save_zone_aggregates(self, df: DataFrame) -> None:
        """Write zone-level aggregates to Parquet."""
        path = self.config.zone_agg_path
        df.write.mode("overwrite").parquet(path)
        logger.info("Zone aggregates written → %s", path)
