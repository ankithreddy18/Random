"""
Professional visualisation suite for the NYC Taxi EV Charging project.

All charts are saved as high-DPI PNG files under outputs/charts/.
"""

import os
import logging
import math
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # non-interactive backend — safe for all envs
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import seaborn as sns

from config import Config, EXISTING_EV_STATIONS

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------
PALETTE_CLUSTERS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf",
]
BOROUGH_COLORS = {
    "Manhattan":    "#e63946",
    "Brooklyn":     "#457b9d",
    "Queens":       "#2a9d8f",
    "Bronx":        "#e9c46a",
    "Staten Island":"#264653",
    "EWR":          "#6d6875",
}

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    "figure.dpi":       150,
    "savefig.dpi":      150,
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "font.family":      "DejaVu Sans",
})


def _save(fig, name: str, charts_dir: str) -> None:
    path = os.path.join(charts_dir, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Chart saved → %s", path)


# ---------------------------------------------------------------------------
# Individual chart functions (used by notebook too)
# ---------------------------------------------------------------------------

def plot_demand_by_hour(trip_pdf: pd.DataFrame, charts_dir: str) -> None:
    """Bar chart — trip count by pickup hour."""
    hourly = trip_pdf.groupby("pickup_hour")["trip_count_proxy"].sum().reset_index()
    hourly.columns = ["hour", "trips"]

    fig, ax = plt.subplots(figsize=(13, 6))
    colors  = ["#e63946" if h in range(7, 10) or h in range(16, 20)
               else "#457b9d" for h in hourly["hour"]]
    bars = ax.bar(hourly["hour"], hourly["trips"], color=colors,
                  edgecolor="white", linewidth=0.5, width=0.85)

    ax.set_xlabel("Hour of Day (24-hour)", fontsize=13)
    ax.set_ylabel("Total Trips", fontsize=13)
    ax.set_title("NYC Taxi Trip Demand by Hour of Day\n"
                 "(Red = Rush Hours: 7–9 am & 4–7 pm)", fontsize=15, fontweight="bold")
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    red_patch  = mpatches.Patch(color="#e63946", label="Rush Hours")
    blue_patch = mpatches.Patch(color="#457b9d", label="Off-Peak Hours")
    ax.legend(handles=[red_patch, blue_patch], fontsize=11)
    ax.grid(axis="y", alpha=0.4)
    fig.tight_layout()
    _save(fig, "01_demand_by_hour.png", charts_dir)


def plot_borough_comparison(zone_pdf: pd.DataFrame, charts_dir: str) -> None:
    """Horizontal bar chart — total trips by borough."""
    borough_trips = (
        zone_pdf.groupby("borough")["total_trips"]
        .sum()
        .sort_values()
        .reset_index()
    )
    borough_trips.columns = ["borough", "trips"]

    colors = [BOROUGH_COLORS.get(b, "#888") for b in borough_trips["borough"]]

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(borough_trips["borough"], borough_trips["trips"],
                   color=colors, edgecolor="white", height=0.65)

    for bar in bars:
        w = bar.get_width()
        ax.text(w + max(borough_trips["trips"]) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{w:,.0f}", va="center", fontsize=11)

    ax.set_xlabel("Total Trip Count", fontsize=13)
    ax.set_title("NYC Taxi Trip Volume by Borough", fontsize=15, fontweight="bold")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="x", alpha=0.4)
    fig.tight_layout()
    _save(fig, "02_borough_comparison.png", charts_dir)


def plot_trip_distance_distribution(zone_pdf: pd.DataFrame, charts_dir: str) -> None:
    """Histogram with KDE — distribution of average trip distances."""
    fig, ax = plt.subplots(figsize=(11, 6))
    data = zone_pdf["avg_distance"].dropna()
    ax.hist(data, bins=30, color="#457b9d", edgecolor="white",
            alpha=0.8, density=True)

    from scipy.stats import gaussian_kde
    try:
        kde_x  = np.linspace(data.min(), min(data.max(), 25), 300)
        kde_y  = gaussian_kde(data)(kde_x)
        ax.plot(kde_x, kde_y, color="#e63946", linewidth=2.5, label="KDE")
    except Exception:
        pass

    ax.axvline(data.mean(), color="#2ca02c", linestyle="--",
               linewidth=2, label=f"Mean = {data.mean():.2f} mi")
    ax.axvline(data.median(), color="#ff7f0e", linestyle="--",
               linewidth=2, label=f"Median = {data.median():.2f} mi")
    ax.set_xlabel("Average Trip Distance (miles)", fontsize=13)
    ax.set_ylabel("Density", fontsize=13)
    ax.set_title("Distribution of Zone-Level Average Trip Distances", fontsize=15,
                 fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(alpha=0.4)
    fig.tight_layout()
    _save(fig, "03_trip_distance_distribution.png", charts_dir)


def plot_cluster_map(zone_pdf: pd.DataFrame, charts_dir: str) -> None:
    """Scatter-map of NYC zones coloured by KMeans cluster assignment."""
    fig, ax = plt.subplots(figsize=(13, 11))
    ax.set_facecolor("#f0f4f8")

    n_clusters = int(zone_pdf["cluster"].max()) + 1
    for c in range(n_clusters):
        subset = zone_pdf[zone_pdf["cluster"] == c]
        color  = PALETTE_CLUSTERS[c % len(PALETTE_CLUSTERS)]
        sizes  = 80 + (subset["total_trips"] / zone_pdf["total_trips"].max() * 400)
        ax.scatter(
            subset["lon"], subset["lat"],
            s=sizes, c=color, alpha=0.85,
            edgecolors="white", linewidths=0.6,
            label=f"Cluster {c}",
        )

    # Rough NYC borough outlines (simplified rectangles)
    borough_boxes = [
        (-74.02, 40.69, 0.16, 0.18,  "Manhattan"),
        (-74.05, 40.56, 0.24, 0.18,  "Brooklyn"),
        (-73.96, 40.60, 0.30, 0.22,  "Queens"),
        (-73.93, 40.79, 0.23, 0.15,  "Bronx"),
        (-74.26, 40.49, 0.24, 0.20,  "Staten Island"),
    ]
    for x, y, w, h, name in borough_boxes:
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x, y), w, h,
                boxstyle="round,pad=0.005",
                linewidth=1.5, edgecolor="#888", facecolor="none", alpha=0.5,
            )
        )
        ax.text(x + w / 2, y + h + 0.002, name, ha="center",
                fontsize=8, color="#555", style="italic")

    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.set_title(
        "KMeans Cluster Map — NYC Taxi Pickup Zones\n"
        "(Circle size ∝ trip volume)",
        fontsize=14, fontweight="bold",
    )
    ax.legend(title="Cluster", loc="lower left", fontsize=9, ncol=2)
    ax.set_xlim(-74.30, -73.68)
    ax.set_ylim(40.48,  40.95)
    fig.tight_layout()
    _save(fig, "04_cluster_map.png", charts_dir)


def plot_cluster_profiles(cluster_summary: pd.DataFrame, charts_dir: str) -> None:
    """Grouped bar chart comparing key metrics across clusters."""
    metrics = ["avg_trips_per_zone", "avg_distance", "rush_hour_fraction"]
    labels  = ["Avg Trips/Zone", "Avg Distance (mi)", "Rush-Hour Fraction"]

    n = len(cluster_summary)
    x = np.arange(n)
    width = 0.22
    fig, ax = plt.subplots(figsize=(14, 7))

    for i, (col, lbl) in enumerate(zip(metrics, labels)):
        vals = cluster_summary[col]
        # Normalise to 0-1 for comparability
        normed = (vals - vals.min()) / (vals.max() - vals.min() + 1e-9)
        offset = (i - 1) * width
        ax.bar(x + offset, normed, width, label=lbl,
               color=PALETTE_CLUSTERS[i], edgecolor="white", alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels([f"Cluster {c}" for c in cluster_summary["cluster"]],
                       rotation=30, ha="right")
    ax.set_ylabel("Normalised Value (0–1)", fontsize=13)
    ax.set_title("KMeans Cluster Profiles — Key Metric Comparison\n"
                 "(Values normalised within each metric)", fontsize=14,
                 fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.4)
    fig.tight_layout()
    _save(fig, "05_cluster_profiles.png", charts_dir)


def plot_ev_recommendations(recommendations: pd.DataFrame,
                            zone_pdf: pd.DataFrame,
                            charts_dir: str) -> None:
    """Map showing all zones, existing chargers, and recommended locations."""
    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_facecolor("#eaf4fb")

    # All zones (grey)
    ax.scatter(
        zone_pdf["lon"], zone_pdf["lat"],
        s=40, c="#cccccc", alpha=0.6, label="All Zones",
        edgecolors="white", linewidths=0.3, zorder=2,
    )

    # Existing EV stations (blue triangles)
    ev_lons = [s[2] for s in EXISTING_EV_STATIONS]
    ev_lats = [s[1] for s in EXISTING_EV_STATIONS]
    ax.scatter(
        ev_lons, ev_lats,
        s=180, c="#1f77b4", marker="^", alpha=0.9,
        label="Existing EV Stations", edgecolors="white",
        linewidths=1.0, zorder=4,
    )

    # Recommended zones (red stars)
    ax.scatter(
        recommendations["lon"], recommendations["lat"],
        s=350, c="#e63946", marker="*", alpha=1.0,
        label="Recommended New Sites", edgecolors="white",
        linewidths=0.8, zorder=5,
    )

    # Annotate top-5 recommendations
    for _, row in recommendations.head(5).iterrows():
        ax.annotate(
            f"#{int(row['rank'])} {row['zone_name'][:18]}",
            (row["lon"], row["lat"]),
            xytext=(8, 8), textcoords="offset points",
            fontsize=8, color="#c0392b",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7),
        )

    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.set_title(
        "EV Charging Station Gap Analysis — NYC\n"
        "★ = Recommended New Sites  ▲ = Existing Stations",
        fontsize=14, fontweight="bold",
    )
    ax.legend(fontsize=11, loc="lower left")
    ax.set_xlim(-74.30, -73.68)
    ax.set_ylim(40.48,  40.95)
    ax.grid(alpha=0.35)
    fig.tight_layout()
    _save(fig, "06_ev_recommendations_map.png", charts_dir)


def plot_sustainability_impact(recommendations: pd.DataFrame,
                               charts_dir: str) -> None:
    """Bar chart — estimated annual CO₂ savings per recommended zone."""
    df = recommendations.sort_values("annual_co2_saved_tonnes", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    colors  = plt.cm.Greens(
        np.linspace(0.4, 0.9, len(df))
    )
    bars = ax.barh(
        df["zone_name"], df["annual_co2_saved_tonnes"],
        color=colors, edgecolor="white",
    )

    for bar in bars:
        w = bar.get_width()
        ax.text(w + df["annual_co2_saved_tonnes"].max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{w:,.1f} t", va="center", fontsize=10)

    total = df["annual_co2_saved_tonnes"].sum()
    ax.set_xlabel("Annual CO₂ Saved (metric tonnes)", fontsize=13)
    ax.set_title(
        f"Estimated Annual CO₂ Savings from EV Infrastructure\n"
        f"Total across top-{len(df)} zones: {total:,.1f} metric tonnes/year",
        fontsize=14, fontweight="bold",
    )
    ax.grid(axis="x", alpha=0.4)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    fig.tight_layout()
    _save(fig, "07_sustainability_impact.png", charts_dir)


def plot_regression_comparison(regression_results: dict,
                                charts_dir: str) -> None:
    """Side-by-side bar chart comparing LR vs GBT metrics."""
    models = ["Linear Regression", "Gradient Boosted Trees"]
    rmse   = [regression_results["linear_regression"]["rmse"],
              regression_results["gbt"]["rmse"]]
    r2     = [regression_results["linear_regression"]["r2"],
              regression_results["gbt"]["r2"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))

    ax1.bar(models, rmse, color=["#457b9d", "#e63946"],
            edgecolor="white", width=0.5)
    for i, v in enumerate(rmse):
        ax1.text(i, v + max(rmse) * 0.01, f"{v:.3f}", ha="center",
                 fontsize=12, fontweight="bold")
    ax1.set_ylabel("RMSE (lower is better)", fontsize=12)
    ax1.set_title("RMSE Comparison", fontsize=13, fontweight="bold")
    ax1.grid(axis="y", alpha=0.4)

    ax2.bar(models, r2, color=["#457b9d", "#e63946"],
            edgecolor="white", width=0.5)
    for i, v in enumerate(r2):
        ax2.text(i, v + max(r2) * 0.01, f"{v:.4f}", ha="center",
                 fontsize=12, fontweight="bold")
    ax2.set_ylabel("R² Score (higher is better)", fontsize=12)
    ax2.set_title("R² Score Comparison", fontsize=13, fontweight="bold")
    ax2.set_ylim(0, 1.05)
    ax2.grid(axis="y", alpha=0.4)

    fig.suptitle("Demand Prediction Model Comparison\nLinear Regression vs GBT Regressor",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    _save(fig, "08_regression_comparison.png", charts_dir)


def plot_feature_importance(regression_results: dict, charts_dir: str) -> None:
    """Horizontal bar chart — GBT feature importances."""
    fi  = regression_results.get("feature_importances", {})
    if not fi:
        return
    features = list(fi.keys())
    values   = [fi[f] for f in features]
    sorted_idx = np.argsort(values)
    features_s = [features[i] for i in sorted_idx]
    values_s   = [values[i]   for i in sorted_idx]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(features_s, values_s, color="#2ca02c", edgecolor="white")
    ax.set_xlabel("Feature Importance (GBT)", fontsize=12)
    ax.set_title("GBT Regressor — Feature Importances\n"
                 "for Trip Demand Prediction", fontsize=14, fontweight="bold")
    ax.grid(axis="x", alpha=0.4)
    fig.tight_layout()
    _save(fig, "09_feature_importance.png", charts_dir)


def plot_elbow_curve(elbow_results: dict, charts_dir: str) -> None:
    """Elbow curve for KMeans k selection."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    ax1.plot(elbow_results["k"], elbow_results["wssse"],
             "o-", color="#e63946", linewidth=2.5, markersize=8)
    ax1.set_xlabel("Number of Clusters (k)", fontsize=12)
    ax1.set_ylabel("Within-Cluster Sum of Squared Errors", fontsize=12)
    ax1.set_title("Elbow Curve — WSSSE vs k", fontsize=13, fontweight="bold")
    ax1.grid(alpha=0.4)

    ax2.plot(elbow_results["k"], elbow_results["silhouette"],
             "s-", color="#457b9d", linewidth=2.5, markersize=8)
    ax2.set_xlabel("Number of Clusters (k)", fontsize=12)
    ax2.set_ylabel("Silhouette Score", fontsize=12)
    ax2.set_title("Silhouette Score vs k", fontsize=13, fontweight="bold")
    ax2.grid(alpha=0.4)

    fig.suptitle("KMeans Hyperparameter Selection", fontsize=14, fontweight="bold")
    fig.tight_layout()
    _save(fig, "10_elbow_curve.png", charts_dir)


# ---------------------------------------------------------------------------
# Orchestrator class
# ---------------------------------------------------------------------------

class Visualizer:

    def __init__(self, config: Config):
        self.config = config
        os.makedirs(config.CHARTS_DIR, exist_ok=True)

    def generate_all(
        self,
        df_features,        # Spark DataFrame (trip-level with features)
        df_clustered,       # Spark DataFrame (zone-level + cluster column)
        cluster_summary: pd.DataFrame,
        recommendations: pd.DataFrame,
        regression_results: dict,
    ) -> None:
        """Generate and save all project charts."""

        # Convert just what we need to Pandas
        logger.info("Converting Spark DataFrames to Pandas for visualisation …")

        # Zone aggregates
        zone_pdf = (
            df_clustered
            .select("PULocationID", "borough", "lat", "lon",
                    "total_trips", "avg_distance", "rush_hour_fraction", "cluster")
            .toPandas()
            .dropna(subset=["lat", "lon"])
        )

        # Hourly demand proxy (PySpark groupby — small result)
        hourly_pdf = (
            df_features
            .groupBy("pickup_hour")
            .count()
            .orderBy("pickup_hour")
            .toPandas()
            .rename(columns={"count": "trip_count_proxy"})
        )
        # We need trip_count_proxy in a combined df for plot_demand_by_hour
        trip_pdf = hourly_pdf.rename(columns={"pickup_hour": "pickup_hour"})

        logger.info("Rendering charts …")

        # Build a minimal DataFrame for demand-by-hour
        demand_df = pd.DataFrame({
            "pickup_hour":       hourly_pdf["pickup_hour"],
            "trip_count_proxy":  hourly_pdf["trip_count_proxy"],
        })

        plot_demand_by_hour(demand_df, self.config.CHARTS_DIR)
        plot_borough_comparison(zone_pdf, self.config.CHARTS_DIR)
        plot_trip_distance_distribution(zone_pdf, self.config.CHARTS_DIR)
        plot_cluster_map(zone_pdf, self.config.CHARTS_DIR)
        plot_cluster_profiles(cluster_summary, self.config.CHARTS_DIR)
        plot_ev_recommendations(recommendations, zone_pdf, self.config.CHARTS_DIR)
        plot_sustainability_impact(recommendations, self.config.CHARTS_DIR)
        plot_regression_comparison(regression_results, self.config.CHARTS_DIR)
        plot_feature_importance(regression_results, self.config.CHARTS_DIR)

        logger.info("All charts saved to %s", self.config.CHARTS_DIR)
