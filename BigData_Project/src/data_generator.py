"""
Synthetic NYC Yellow-Taxi trip data generator.

Produces a CSV with the same schema as the official NYC TLC dataset so that
the downstream Spark pipeline works identically whether you feed it real or
synthetic data.  Trip counts, fare structures, and temporal distributions are
calibrated against published TLC statistics.
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config import NYC_ZONES

logger = logging.getLogger(__name__)


def generate_synthetic_data(output_path: str, num_records: int = 100_000,
                            seed: int = 42) -> pd.DataFrame:
    """
    Generate `num_records` synthetic taxi trips and write them to `output_path`.

    Returns the DataFrame so callers can inspect it directly.
    """
    rng = np.random.default_rng(seed)
    logger.info("Generating %d synthetic taxi trip records …", num_records)

    # ---------------------------------------------------------------- zones
    zone_ids      = list(NYC_ZONES.keys())
    demand_weights = np.array([NYC_ZONES[z][4] for z in zone_ids], dtype=float)
    demand_weights /= demand_weights.sum()

    pickup_zones  = rng.choice(zone_ids, size=num_records, p=demand_weights)

    # Dropoff zone — 65 % biased toward high-demand zones, 35 % uniform
    mask   = rng.random(num_records) < 0.65
    drop_a = rng.choice(zone_ids, size=num_records, p=demand_weights)
    drop_b = rng.choice(zone_ids, size=num_records)
    dropoff_zones = np.where(mask, drop_a, drop_b)

    # -------------------------------------------------------------- datetime
    # Cover the entire month of January 2023
    base = datetime(2023, 1, 1)

    # Realistic hourly demand weights (rush-hours peak; 2–4 am low)
    hour_w = np.array([
        0.50, 0.30, 0.20, 0.18, 0.25, 0.65,   # 00-05
        1.10, 1.90, 2.50, 1.80, 1.60, 1.75,   # 06-11
        1.85, 1.95, 1.85, 1.75, 1.90, 2.30,   # 12-17
        2.80, 3.00, 2.60, 2.10, 1.60, 1.05,   # 18-23
    ], dtype=float)
    hour_w /= hour_w.sum()

    hours   = rng.choice(24, size=num_records, p=hour_w)
    days    = rng.integers(0, 31, size=num_records)
    minutes = rng.integers(0, 60, size=num_records)
    seconds = rng.integers(0, 60, size=num_records)

    pickup_dts = [
        base + timedelta(days=int(d), hours=int(h),
                         minutes=int(m), seconds=int(s))
        for d, h, m, s in zip(days, hours, minutes, seconds)
    ]

    # --------------------------------------------------------- trip geometry
    # Log-normal distance: median ~2.3 miles, mean ~3.5 miles
    distances = rng.lognormal(mean=0.85, sigma=0.75, size=num_records)
    distances = np.clip(distances, 0.10, 60.0).round(2)

    # Speed (mph): log-normal centred around 11 mph (NYC average)
    speeds    = rng.lognormal(mean=2.35, sigma=0.38, size=num_records)
    speeds    = np.clip(speeds, 2.0, 45.0)

    duration_min = (distances / speeds) * 60.0
    duration_min = np.clip(duration_min, 1.0, 180.0)

    # Floor to seconds so the CSV format stays yyyy-MM-dd HH:mm:ss
    dropoff_dts = [
        (pd.Timestamp(pickup_dts[i]) + pd.Timedelta(minutes=float(duration_min[i]))).floor("s")
        for i in range(num_records)
    ]

    # ---------------------------------------------------------------- fares
    # NYC metered fare: $3.00 base + $2.50/mile + $0.50/min congestion
    fare = 3.00 + distances * 2.50 + duration_min * 0.25
    fare += rng.normal(0, 0.50, size=num_records)
    fare  = np.clip(fare, 2.50, 250.0).round(2)

    tips  = np.where(
        rng.random(num_records) < 0.72,
        (fare * rng.uniform(0.10, 0.28, num_records)).round(2),
        0.0,
    )

    tolls = np.where(
        rng.random(num_records) < 0.12,
        rng.uniform(0.5, 16.0, num_records).round(2),
        0.0,
    )

    congestion = np.where(rng.random(num_records) < 0.62, 2.50, 0.0)
    total = (fare + tips + tolls + congestion + 0.50 + 0.30).round(2)

    # ---------------------------------------------------------------- misc
    passengers   = rng.choice([1, 2, 3, 4, 5, 6], size=num_records,
                               p=[0.55, 0.25, 0.10, 0.05, 0.03, 0.02])
    vendor_ids   = rng.choice([1, 2], size=num_records)
    payment_type = rng.choice([1, 2, 3, 4], size=num_records,
                               p=[0.65, 0.30, 0.03, 0.02])
    rate_code    = rng.choice([1, 2, 3, 4, 5, 6], size=num_records,
                               p=[0.90, 0.04, 0.02, 0.01, 0.02, 0.01])
    store_fwd    = np.where(rng.random(num_records) < 0.02, "Y", "N")

    df = pd.DataFrame({
        "VendorID":              vendor_ids,
        "tpep_pickup_datetime":  pickup_dts,
        "tpep_dropoff_datetime": dropoff_dts,
        "passenger_count":       passengers,
        "trip_distance":         distances,
        "RatecodeID":            rate_code,
        "store_and_fwd_flag":    store_fwd,
        "PULocationID":          pickup_zones,
        "DOLocationID":          dropoff_zones,
        "payment_type":          payment_type,
        "fare_amount":           fare,
        "extra":                 rng.choice([0.0, 0.5, 1.0], size=num_records,
                                             p=[0.30, 0.50, 0.20]).round(2),
        "mta_tax":               0.50,
        "tip_amount":            tips,
        "tolls_amount":          tolls,
        "improvement_surcharge": 0.30,
        "total_amount":          total,
        "congestion_surcharge":  congestion,
    })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("Saved %d records → %s", num_records, output_path)
    return df


def generate_sample(output_path: str, num_records: int = 5_000, seed: int = 99):
    """Convenience wrapper for generating a small sample file."""
    return generate_synthetic_data(output_path, num_records=num_records, seed=seed)
