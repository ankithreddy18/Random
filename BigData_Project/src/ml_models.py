"""
Spark MLlib model implementations.

Models
------
1. KMeans clustering      — identify high-traffic mobility zones
2. Linear Regression      — baseline demand prediction
3. GBT Regression         — advanced demand prediction

Both regression models predict `trip_count` for a given zone/hour combination.
"""

import logging
import os
import json

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans, KMeansModel
from pyspark.ml.regression import LinearRegression, GBTRegressor
from pyspark.ml.evaluation import (
    ClusteringEvaluator,
    RegressionEvaluator,
)
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

from config import Config

logger = logging.getLogger(__name__)


class MLModels:
    """Wrapper around all Spark MLlib models used in this project."""

    def __init__(self, spark: SparkSession, config: Config):
        self.spark  = spark
        self.config = config

    # ================================================================ KMeans

    def run_kmeans(self, zone_agg_df: DataFrame):
        """
        Fit KMeans on zone-level aggregate features.

        Returns
        -------
        df_clustered    : zone_agg_df with an added `cluster` column
        model           : fitted KMeansModel
        cluster_summary : pandas DataFrame summarising each cluster
        """
        logger.info("Fitting KMeans (k=%d) …", self.config.NUM_CLUSTERS)

        feature_cols = [
            "total_trips", "avg_distance", "avg_fare",
            "avg_speed_mph", "rush_hour_fraction", "weekend_fraction",
            "avg_duration_min",
        ]

        # Drop rows with any null in the feature columns
        df_clean = zone_agg_df.dropna(subset=feature_cols)

        assembler = VectorAssembler(
            inputCols=feature_cols,
            outputCol="raw_features",
        )
        scaler = StandardScaler(
            inputCol="raw_features",
            outputCol="features",
            withMean=True,
            withStd=True,
        )
        kmeans = KMeans(
            featuresCol="features",
            predictionCol="cluster",
            k=self.config.NUM_CLUSTERS,
            maxIter=self.config.KMEANS_MAX_ITER,
            seed=self.config.KMEANS_SEED,
        )
        pipeline = Pipeline(stages=[assembler, scaler, kmeans])
        model    = pipeline.fit(df_clean)

        df_clustered = model.transform(df_clean)

        # Evaluate
        evaluator = ClusteringEvaluator(
            featuresCol="features",
            predictionCol="cluster",
        )
        silhouette = evaluator.evaluate(df_clustered)
        logger.info("KMeans silhouette score: %.4f", silhouette)

        # Cluster summary (convert to Pandas for reporting)
        cluster_summary = (
            df_clustered
            .groupBy("cluster")
            .agg(
                F.count("*")                    .alias("num_zones"),
                F.sum("total_trips")            .alias("total_trips"),
                F.avg("total_trips")            .alias("avg_trips_per_zone"),
                F.avg("avg_distance")           .alias("avg_distance"),
                F.avg("avg_fare")               .alias("avg_fare"),
                F.avg("rush_hour_fraction")     .alias("rush_hour_fraction"),
                F.avg("weekend_fraction")       .alias("weekend_fraction"),
                F.avg("lat")                    .alias("centroid_lat"),
                F.avg("lon")                    .alias("centroid_lon"),
                F.first("borough")              .alias("dominant_borough"),
            )
            .orderBy("cluster")
            .toPandas()
        )
        cluster_summary["silhouette"] = silhouette

        # Save summary
        out_path = os.path.join(self.config.RESULTS_DIR, "cluster_summary.json")
        cluster_summary.to_json(out_path, orient="records", indent=2)
        logger.info("Cluster summary saved → %s", out_path)

        return df_clustered, model, cluster_summary

    def find_optimal_k(self, zone_agg_df: DataFrame,
                       k_range=range(2, 12)) -> dict:
        """
        Run KMeans for multiple k values, returning WSSSE and silhouette.
        Used for the elbow-curve chart.
        """
        feature_cols = [
            "total_trips", "avg_distance", "avg_fare",
            "avg_speed_mph", "rush_hour_fraction", "weekend_fraction",
            "avg_duration_min",
        ]
        df_clean  = zone_agg_df.dropna(subset=feature_cols)
        assembler = VectorAssembler(inputCols=feature_cols,
                                   outputCol="raw_features")
        scaler    = StandardScaler(inputCol="raw_features",
                                   outputCol="features",
                                   withMean=True, withStd=True)

        prep_pipeline = Pipeline(stages=[assembler, scaler])
        df_prep = prep_pipeline.fit(df_clean).transform(df_clean)
        df_prep.cache()

        results = {"k": [], "wssse": [], "silhouette": []}
        evaluator = ClusteringEvaluator(featuresCol="features",
                                        predictionCol="cluster")

        for k in k_range:
            km    = KMeans(k=k, featuresCol="features",
                           predictionCol="cluster",
                           seed=self.config.KMEANS_SEED)
            model = km.fit(df_prep)
            df_p  = model.transform(df_prep)
            wssse = model.summary.trainingCost
            sil   = evaluator.evaluate(df_p)
            results["k"].append(k)
            results["wssse"].append(wssse)
            results["silhouette"].append(sil)
            logger.info("k=%d  WSSSE=%.2f  silhouette=%.4f", k, wssse, sil)

        df_prep.unpersist()
        return results

    # ============================================================ Regression

    def run_regression(self, hourly_demand_df: DataFrame) -> dict:
        """
        Train Linear Regression and GBT Regressor to predict `trip_count`.

        Returns a dict with eval metrics and feature importance for both
        models.
        """
        logger.info("Training demand-prediction regression models …")

        feature_cols = [
            "PULocationID", "pickup_hour", "pickup_dow",
            "is_weekend", "is_rush_hour", "avg_distance", "avg_fare",
        ]

        df_clean = (
            hourly_demand_df
            .dropna(subset=feature_cols + ["trip_count"])
            .filter(F.col("trip_count") > 0)
        )
        df_clean.cache()

        # ---- feature prep shared by both models
        assembler = VectorAssembler(inputCols=feature_cols,
                                    outputCol="features")

        train_df, test_df = df_clean.randomSplit(
            [self.config.TRAIN_RATIO, self.config.TEST_RATIO],
            seed=self.config.RANDOM_SEED,
        )

        results = {}

        # ---- Linear Regression (baseline)
        lr = LinearRegression(
            featuresCol="features",
            labelCol="trip_count",
            maxIter=100,
            regParam=0.01,
            elasticNetParam=0.0,
        )
        lr_pipeline = Pipeline(stages=[assembler, lr])
        lr_model    = lr_pipeline.fit(train_df)
        lr_preds    = lr_model.transform(test_df)
        results["linear_regression"] = self._eval_regression(lr_preds,
                                                              "trip_count",
                                                              "Linear Regression")

        # ---- Gradient-Boosted Trees (advanced)
        gbt = GBTRegressor(
            featuresCol="features",
            labelCol="trip_count",
            maxIter=50,
            maxDepth=5,
            stepSize=0.1,
            seed=self.config.RANDOM_SEED,
        )
        gbt_pipeline = Pipeline(stages=[assembler, gbt])
        gbt_model    = gbt_pipeline.fit(train_df)
        gbt_preds    = gbt_model.transform(test_df)
        results["gbt"] = self._eval_regression(gbt_preds,
                                                "trip_count",
                                                "Gradient Boosted Trees")

        # Feature importances from GBT
        gbt_stage = gbt_model.stages[-1]
        results["feature_importances"] = dict(
            zip(feature_cols, [float(x) for x in gbt_stage.featureImportances])
        )
        logger.info("GBT feature importances: %s",
                    results["feature_importances"])

        # Save results
        out_path = os.path.join(self.config.RESULTS_DIR, "regression_results.json")
        with open(out_path, "w") as fh:
            json.dump(results, fh, indent=2)
        logger.info("Regression results saved → %s", out_path)

        df_clean.unpersist()
        return results

    @staticmethod
    def _eval_regression(predictions: DataFrame,
                         label_col: str,
                         model_name: str) -> dict:
        """Compute RMSE, MAE, R² for a predictions DataFrame."""
        ev = RegressionEvaluator(labelCol=label_col,
                                 predictionCol="prediction")
        rmse = ev.setMetricName("rmse").evaluate(predictions)
        mae  = ev.setMetricName("mae").evaluate(predictions)
        r2   = ev.setMetricName("r2").evaluate(predictions)
        logger.info(
            "%s → RMSE=%.3f  MAE=%.3f  R²=%.4f",
            model_name, rmse, mae, r2,
        )
        return {"model": model_name, "rmse": rmse, "mae": mae, "r2": r2}
