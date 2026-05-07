"""
EV Charging Station Recommendation Engine.

Algorithm
---------
1. Score every zone by demand intensity (trips × rush-hour fraction).
2. For each zone, compute the distance to the nearest existing EV charger.
3. Zones that are high-demand AND poorly served (distance > coverage radius)
   are flagged as underserved.
4. Rank by a combined priority score.
5. Output the top-N recommendations with estimated sustainability impact.
"""

import logging
import math
import os
import json

import pandas as pd
import numpy as np

from config import Config, NYC_ZONES, EXISTING_EV_STATIONS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Haversine distance helper
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float,
                  lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres."""
    R = 6371.0
    φ1, φ2   = math.radians(lat1), math.radians(lat2)
    Δφ       = math.radians(lat2 - lat1)
    Δλ       = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _min_distance_to_charger(lat: float, lon: float) -> float:
    """Return the distance (km) to the nearest existing EV charging station."""
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        return float("inf")
    return min(
        _haversine_km(lat, lon, s[1], s[2])
        for s in EXISTING_EV_STATIONS
    )


def _count_chargers_within(lat: float, lon: float, radius_km: float) -> int:
    """Count EV stations within `radius_km` of (lat, lon)."""
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        return 0
    return sum(
        1 for s in EXISTING_EV_STATIONS
        if _haversine_km(lat, lon, s[1], s[2]) <= radius_km
    )


# ---------------------------------------------------------------------------
# Main recommender
# ---------------------------------------------------------------------------

class EVRecommender:

    def __init__(self, config: Config):
        self.config = config

    def generate_recommendations(
        self,
        df_clustered,           # Spark DataFrame — output of KMeans transform
        cluster_summary: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build a ranked list of zones that need new EV charging stations.

        Parameters
        ----------
        df_clustered    : Spark DataFrame with zone aggregates + `cluster` col
        cluster_summary : pandas DataFrame (one row per cluster)

        Returns
        -------
        recommendations : pandas DataFrame with priority-ranked zone suggestions
        """

        # Convert zone-level data to Pandas for distance computations
        zone_pdf = (
            df_clustered
            .select(
                "PULocationID", "borough", "lat", "lon",
                "total_trips", "rush_hour_fraction",
                "avg_distance", "avg_fare", "cluster",
            )
            .toPandas()
        )

        zone_pdf = zone_pdf.dropna(subset=["lat", "lon"])

        # ---- Demand intensity score (normalised 0-1)
        max_trips = zone_pdf["total_trips"].max()
        zone_pdf["demand_score"] = (
            zone_pdf["total_trips"] / max_trips * 0.7 +
            zone_pdf["rush_hour_fraction"]           * 0.3
        )

        # ---- Spatial service gap
        zone_pdf["nearest_station_km"] = zone_pdf.apply(
            lambda r: _min_distance_to_charger(r["lat"], r["lon"]), axis=1
        )
        zone_pdf["chargers_within_1km"] = zone_pdf.apply(
            lambda r: _count_chargers_within(
                r["lat"], r["lon"], self.config.EV_COVERAGE_RADIUS_KM
            ),
            axis=1,
        )

        # ---- Service gap score: 1 if totally unserved, 0 if well served
        max_dist = zone_pdf["nearest_station_km"].replace(float("inf"), 30.0).max()
        zone_pdf["nearest_station_km_clipped"] = zone_pdf["nearest_station_km"].clip(upper=30.0)
        zone_pdf["gap_score"] = zone_pdf["nearest_station_km_clipped"] / max_dist

        # ---- Priority score — high demand + high gap = top priority
        zone_pdf["priority_score"] = (
            0.60 * zone_pdf["demand_score"] +
            0.40 * zone_pdf["gap_score"]
        )

        # ---- Adaptive hotspot threshold: configured value OR top-40% of zones,
        #      whichever is lower — ensures recommendations are always produced.
        adaptive_threshold = min(
            self.config.MIN_TRIPS_FOR_HOTSPOT,
            float(zone_pdf["total_trips"].quantile(0.60)),
        )
        hotspots = zone_pdf[
            zone_pdf["total_trips"] >= adaptive_threshold
        ].copy()

        # ---- Exclude zones already well-covered
        underserved = hotspots[
            hotspots["chargers_within_1km"] < 2
        ].copy()

        recommendations = (
            underserved
            .sort_values("priority_score", ascending=False)
            .head(self.config.TOP_N_RECOMMENDATIONS)
            .reset_index(drop=True)
        )

        # ---- Enrich with zone name
        recommendations["zone_name"] = recommendations["PULocationID"].map(
            lambda z: NYC_ZONES.get(z, (f"Zone {z}",))[0]
        )

        # ---- Sustainability estimate
        co2_save_per_trip = (
            self.config.GASOLINE_CO2_PER_MILE - self.config.EV_CO2_PER_MILE
        ) * recommendations["avg_distance"]  # grams saved per trip
        # Assume 30 % EV adoption once charging infrastructure is in place
        ev_adoption_rate = 0.30
        annual_multiplier = 12  # we have 1-month synthetic data

        recommendations["annual_trips_est"] = (
            recommendations["total_trips"] * annual_multiplier
        ).astype(int)
        recommendations["annual_co2_saved_kg"] = (
            recommendations["annual_trips_est"]
            * ev_adoption_rate
            * co2_save_per_trip
            / 1000.0
        ).round(0).astype(int)
        recommendations["annual_co2_saved_tonnes"] = (
            recommendations["annual_co2_saved_kg"] / 1000.0
        ).round(1)

        recommendations["rank"] = recommendations.index + 1

        # ---- Save
        out_path = os.path.join(self.config.RESULTS_DIR,
                                "ev_recommendations.json")
        recommendations.to_json(out_path, orient="records", indent=2)
        logger.info(
            "Top-%d EV recommendations saved → %s",
            len(recommendations),
            out_path,
        )
        self._print_summary(recommendations)
        return recommendations

    @staticmethod
    def _print_summary(recs: pd.DataFrame) -> None:
        total_co2 = recs["annual_co2_saved_tonnes"].sum()
        print("\n" + "=" * 65)
        print("  EV CHARGING STATION RECOMMENDATIONS")
        print("=" * 65)
        print(f"  {'Rank':<5} {'Zone':<35} {'Borough':<15} {'Score':>6}")
        print("-" * 65)
        for _, row in recs.iterrows():
            print(
                f"  {int(row['rank']):<5} {row['zone_name']:<35} "
                f"{row['borough']:<15} {row['priority_score']:>6.3f}"
            )
        print("-" * 65)
        print(f"  Estimated annual CO₂ savings if top-10 zones are served:")
        print(f"  {total_co2:,.1f} metric tonnes CO₂/year")
        print("=" * 65 + "\n")
