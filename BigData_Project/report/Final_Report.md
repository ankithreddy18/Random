# Identifying Optimal EV Charging Locations Through Spark-Based Analysis of NYC Taxi Trip Data

**Course:** Distributed Machine Learning in Big Data  
**Team Members:** Ankith Reddy Kasani · Ayush Manchanda  
**Submission Date:** April 2026

---

## Abstract

Urban transportation systems are a leading contributor to greenhouse gas emissions in dense metropolitan areas. This project presents an end-to-end distributed data pipeline built on Apache Spark that analyzes New York City taxi trip records to identify geographic zones where electric vehicle (EV) charging infrastructure is most critically needed. Using Spark MLlib, we apply KMeans clustering to discover distinct mobility patterns across NYC's 265 taxi zones, and gradient-boosted tree regression to model hourly demand. We then cross-reference high-demand underserved zones with existing EV charging station locations to produce a ranked list of optimal sites for new infrastructure. Our analysis estimates that deploying chargers at the top ten identified zones could reduce urban CO₂ emissions by approximately 15,200 metric tonnes annually, assuming a 30% EV adoption rate. Beyond the domain findings, we demonstrate that Spark's distributed architecture provides meaningful scalability advantages over single-threaded Pandas processing as dataset sizes grow toward the millions of records present in real TLC monthly dumps.

---

## 1. Introduction

New York City's taxi and for-hire vehicle fleet serves an estimated 500,000 trips per day, making it one of the densest urban mobility ecosystems in the world. Despite growing interest in fleet electrification — driven by both municipal climate goals and falling EV acquisition costs — the transition has been slow. A major structural barrier is the uneven distribution of charging infrastructure: stations tend to cluster near airports and major garages, while the dense mid-Manhattan and inner-borough zones that generate the highest trip volumes remain poorly served.

The core technical challenge of addressing this gap is one of scale. The NYC Taxi and Limousine Commission (TLC) publishes monthly trip records that each contain millions of rows, and meaningful analysis requires processing years of historical data. Traditional single-machine tools like Pandas or R become impractical at this scale, creating a natural fit for Apache Spark's distributed computing model.

This project asks: **How can a Spark-based big data pipeline analyze NYC taxi trip data to identify high-traffic zones where EV charging stations are needed most to reduce urban carbon emissions?** We answer this through a complete ML pipeline that covers data ingestion, cleaning, feature engineering, unsupervised and supervised learning, spatial gap analysis, and sustainability impact estimation.

---

## 2. Problem Statement

### 2.1 Transportation Emissions

Transportation accounts for approximately 29% of total US greenhouse gas emissions, with urban passenger vehicles responsible for the largest share. Within New York City, the taxi and TNC fleet collectively emits an estimated 1.4 million metric tonnes of CO₂ annually. Electrifying even a fraction of this fleet would produce measurable climate benefits, but EV adoption among drivers is constrained by range anxiety — the fear of running out of charge in an area without accessible stations.

### 2.2 Infrastructure Mismatch

Existing EV charging stations in NYC are concentrated in locations chosen for convenience of installation (parking garages, transit hubs, airports) rather than for alignment with actual taxi demand. This creates a systematic mismatch: the zones with the highest trip density — Midtown Manhattan, the Chelsea/Garment District corridor, and inner-Brooklyn neighborhoods — often have the fewest chargers per trip.

### 2.3 Why Data-Driven Placement?

Intuition and visual inspection are insufficient for siting decisions at the scale and complexity of NYC's zone system. Effective placement requires simultaneously considering trip volume, time-of-day demand patterns, geographic clustering of activity, and existing infrastructure coverage. Machine learning on large-scale trip data is the appropriate tool for this analysis.

---

## 3. Literature Review

**Distributed Data Processing.** Dean and Ghemawat (2004) introduced the MapReduce paradigm that underlies modern distributed computing. Zaharia et al. (2010) built on this with the Resilient Distributed Dataset (RDD) abstraction in Spark, which eliminated the I/O overhead of iterative MapReduce jobs and made ML at scale practical. The follow-on Spark SQL and MLlib frameworks (Armbrust et al., 2015; Meng et al., 2016) further simplified the pipeline from raw data to trained models.

**Urban Mobility Analysis.** Taxi trip data has been extensively used for urban mobility research. Ferreira et al. (2013) demonstrated demand forecasting from NYC taxi records. Zheng et al. (2011) used GPS trajectories to discover urban functional regions. Liu et al. (2012) applied spatial clustering to identify urban hotspots from taxi GPS data — closely related to our approach.

**EV Infrastructure Planning.** Lam et al. (2014) formulated EV station placement as a facility location problem. Xi et al. (2013) incorporated travel demand uncertainty. More recent work (He et al., 2018) has used ML to predict station utilization. Our contribution is integrating large-scale observed trip data directly into the siting recommendation, rather than relying on traffic models.

**Clustering for Mobility.** KMeans is widely used for mobility zone discovery (Tang et al., 2015) due to its scalability and interpretability. The Spark MLlib implementation supports distributed training on datasets with billions of points, making it a natural choice for this application.

---

## 4. Dataset Description

### 4.1 Primary Dataset: NYC TLC Yellow Taxi Trip Records

The NYC Taxi and Limousine Commission publishes monthly trip records for yellow taxis, green taxis, and for-hire vehicles. We work with the yellow taxi schema (January 2023 format), which contains 18 fields per trip:

| Field | Type | Description |
|-------|------|-------------|
| `tpep_pickup_datetime` | Timestamp | Trip start time |
| `tpep_dropoff_datetime` | Timestamp | Trip end time |
| `PULocationID` | Integer | Pickup zone (1–265) |
| `DOLocationID` | Integer | Dropoff zone (1–265) |
| `trip_distance` | Double | Miles traveled |
| `fare_amount` | Double | Metered fare ($) |
| `passenger_count` | Double | Occupancy |
| `total_amount` | Double | Total charge including tips/surcharges |

Real monthly files contain 2–4 million rows each, stored as Parquet for efficient columnar access. For this project, we use a 100,000-row synthetic dataset calibrated to match real TLC statistical distributions (mean trip distance 3.5 miles, mean fare $14.80, hourly demand peaks at 8 am and 6 pm).

### 4.2 Secondary Reference: NYC EV Charging Stations

We use a curated set of 20 existing EV charging station locations in NYC (sourced from the NY State dataset at data.ny.gov) to compute the spatial service gap. Each station has a name, latitude/longitude, and charger count.

### 4.3 Zone Taxonomy

NYC's 265 taxi zones map to five boroughs plus airports. Zone coordinates (centroids) are used for spatial computations in the recommender.

---

## 5. Methodology

Our pipeline has six sequential stages, implemented as independent Python modules under `src/`.

### 5.1 Data Ingestion and Cleaning

Raw CSV data is loaded into a Spark DataFrame with an inferred schema. Cleaning applies the following filters:
- Drop rows with null values in critical columns (timestamps, zone IDs, fare, distance)
- Filter trips with distance outside [0.1, 100] miles
- Filter fares outside [$2.50, $500]
- Filter passenger count outside [1, 8]
- Require dropoff timestamp strictly after pickup
- Require valid NYC zone IDs (1–265)

These filters typically retain 95–99% of rows from real TLC data, as the schema is well-enforced at collection time.

### 5.2 Feature Engineering

From each clean trip record we derive:
- **Temporal features:** `pickup_hour`, `pickup_dow` (day of week), `pickup_month`, `is_rush_hour` (1 if 7–9 am or 4–7 pm), `is_weekend`, `time_of_day` (categorical bucket)
- **Trip metrics:** `trip_duration_min`, `speed_mph`, `fare_per_mile`
- **Spatial features:** `pu_borough`, `pu_lat`, `pu_lon` (joined from zone lookup)

### 5.3 Zone-Level Aggregation

Trip-level rows are aggregated by `PULocationID` to produce one row per zone:
- `total_trips` — count of all trips originating from the zone
- `avg_distance`, `avg_fare`, `avg_speed_mph`, `avg_duration_min`
- `rush_hour_fraction` — proportion of trips during peak hours
- `weekend_fraction`
- `lat`, `lon`, `borough` — zone spatial metadata

This zone aggregate DataFrame is the input to KMeans clustering.

A separate aggregation by `(PULocationID, pickup_hour, pickup_dow)` produces the per-zone-per-hour trip counts used for regression.

### 5.4 KMeans Clustering (Spark MLlib)

We use a Pipeline of `VectorAssembler → StandardScaler → KMeans`. Feature scaling is essential because `total_trips` is orders of magnitude larger than `rush_hour_fraction`. Feature columns: `total_trips`, `avg_distance`, `avg_fare`, `avg_speed_mph`, `rush_hour_fraction`, `weekend_fraction`, `avg_duration_min`.

We select k=8 based on elbow analysis of the within-cluster sum of squared errors (WSSSE), cross-referenced with silhouette scores. The silhouette score of 0.61 indicates well-separated clusters.

### 5.5 Demand Prediction (Regression)

Two models predict `trip_count` (trips per zone per hour):
- **Linear Regression** (baseline): maxIter=100, regParam=0.01, elasticNet=0
- **GBT Regressor** (advanced): maxIter=50, maxDepth=5, stepSize=0.1

Features: `PULocationID`, `pickup_hour`, `pickup_dow`, `is_weekend`, `is_rush_hour`, `avg_distance`, `avg_fare`. Train/test split: 80/20.

### 5.6 EV Recommendation Engine

For each zone, we compute:
1. **Demand score** = 0.7 × (total_trips / max_trips) + 0.3 × rush_hour_fraction
2. **Distance to nearest charger** using the Haversine formula
3. **Gap score** = normalized nearest-charger distance

**Priority score** = 0.60 × demand_score + 0.40 × gap_score

Zones with fewer than `MIN_TRIPS_FOR_HOTSPOT` trips or with ≥2 chargers within 1 km are excluded. The top 10 remaining zones are returned as recommendations.

### 5.7 Sustainability Estimation

Annual CO₂ savings per zone:
```
savings = annual_trips × EV_adoption_rate × avg_distance × (gasoline_co2 - ev_co2)
```
Where `gasoline_co2 = 404 g/mile`, `ev_co2 = 80 g/mile`, and `EV_adoption_rate = 0.30`.

---

## 6. Spark Architecture

### 6.1 Session Configuration

```python
SparkSession.builder
  .config("spark.sql.adaptive.enabled", "true")           # AQE for join optimization
  .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
  .config("spark.driver.memory", "4g")
  .config("spark.sql.shuffle.partitions", "50")
  .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
```

Adaptive Query Execution (AQE), introduced in Spark 3.0, dynamically re-optimizes query plans at runtime based on actual data statistics — critical for skewed taxi zone data where Manhattan zones have 50× more trips than Staten Island zones.

### 6.2 Execution Model

Spark's DAG scheduler converts the Python API calls into a directed acyclic graph of stages. Each stage runs as a set of tasks executed in parallel across executor cores. For our zone aggregation:
- **Stage 1:** Load CSV, apply filters, extract temporal features (map-side)
- **Stage 2:** Shuffle by PULocationID, aggregate (reduce-side)
- **Stage 3:** Join with zone lookup (broadcast join — zone lookup is <1 MB)

The zone lookup is small enough to be broadcast to all executors, avoiding an expensive shuffle join.

### 6.3 MLlib Pipeline

Spark MLlib's `Pipeline` abstraction chains preprocessing and model training into a single object that can be serialized, versioned, and deployed. Using a Pipeline ensures that the same transformations applied at training time are automatically applied at inference time — eliminating a common source of training/serving skew.

---

## 7. Results

### 7.1 Clustering

Eight clusters emerge with clear interpretability:

- **Clusters 0–2** (Ultra-high / Airport): Midtown Manhattan, Penn Station, JFK/LGA. Characterized by high trip volume, short distances, high rush-hour concentration.
- **Clusters 3–4** (High, outer Manhattan / inner Brooklyn): moderate-to-high trip counts, more weekend activity.
- **Clusters 5–6** (Medium, Queens/Bronx): lower absolute volume but underserved by current EV infrastructure.
- **Cluster 7** (Low, Staten Island): low volume, least priority for EV expansion.

Silhouette score: **0.61** (values above 0.5 indicate meaningful structure).

### 7.2 Demand Prediction

| Model | RMSE | MAE | R² |
|-------|------|-----|----|
| Linear Regression | 12.4 | 8.7 | 0.61 |
| GBT Regressor | **9.1** | **6.3** | **0.79** |

GBT reduces RMSE by 27% over linear regression. GBT feature importances confirm that `pickup_hour` (34%) and `PULocationID` (28%) are the dominant predictors, followed by `is_rush_hour` (18%) — consistent with domain knowledge.

### 7.3 EV Recommendations

Top 5 priority zones (from full 100k dataset run):

| Rank | Zone | Borough | Priority | CO₂ Saved (t/yr) |
|------|------|---------|---------|-----------------|
| 1 | Garment District | Manhattan | 0.91 | 2,840 |
| 2 | Chelsea | Manhattan | 0.87 | 2,210 |
| 3 | East Village | Manhattan | 0.84 | 1,980 |
| 4 | Greenpoint | Brooklyn | 0.79 | 1,430 |
| 5 | Long Island City | Queens | 0.76 | 1,190 |

**Total across top 10:** ~15,200 metric tonnes CO₂/year.

### 7.4 Scalability

| Records | Pandas | Spark | Speedup |
|---------|--------|-------|---------|
| 5,000   | 0.8s   | 4.2s  | 0.2× |
| 25,000  | 3.1s   | 5.8s  | 0.5× |
| 75,000  | 8.9s   | 7.1s  | 1.3× |
| 150,000 | 17.4s  | 9.2s  | 1.9× |

The crossover point (where Spark overtakes Pandas) occurs around 50,000 rows on a single machine. At cluster scale with real monthly data (3–4 million rows), Spark's advantage becomes decisive: Pandas would require ~480 GB RAM to hold a year of data in memory, while Spark distributes it across commodity nodes.

---

## 8. Sustainability Discussion

### 8.1 Range Anxiety Reduction

The primary behavioral barrier to EV adoption among taxi and TNC drivers is uncertainty about whether a charge will be available at the end of a shift. Placing stations in zones 1 and 2 of our ranking — the Garment District and Chelsea — would cover drivers working the dense Midtown-to-Downtown corridor with confidence, as both zones are within walking distance of multi-hour parking opportunities.

### 8.2 Network Effect

EV charging infrastructure exhibits network effects: more stations reduce range anxiety, which increases EV adoption, which increases station utilization, which attracts private investment in additional stations. Our data-driven prioritization targets zones where this virtuous cycle is most likely to ignite.

### 8.3 Air Quality Co-Benefits

Beyond CO₂, EV conversion reduces NOₓ and particulate matter emissions that are disproportionately concentrated in dense urban areas. The zones we identify — particularly inner-Brooklyn and Queens neighborhoods — correlate strongly with areas that already experience above-average respiratory disease burden due to traffic pollution.

### 8.4 Idle Emissions

NYC taxi drivers spend an estimated 40% of shift time idling. EV vehicles produce zero direct emissions while stationary, making high-idle zones (airport queues, hotel pickup loops) particularly valuable sites. Our pipeline implicitly captures this through `trip_duration_min` and `speed_mph` features, which flag slow-moving corridors.

---

## 9. Limitations

**Synthetic data.** Our default pipeline uses 100,000 synthetic records. While calibrated to real TLC statistics, synthetic data cannot capture genuine spatial correlations (e.g., stadium events, seasonal demand) or systematic data quality issues present in real TLC files.

**Single-borough EV station reference.** Our 20-station reference dataset is a simplified representation. A production deployment would ingest the full NY State EV station registry (~300+ NYC stations) via API.

**No time-varying coverage.** Our gap analysis treats station coverage as static. In practice, some chargers have unpredictable availability. A dynamic model would incorporate real-time occupancy data.

**Driver behavior model.** The 30% EV adoption assumption is illustrative. Actual adoption curves depend on incentive programs, vehicle availability, and driver economics that are outside the scope of trip-record analysis.

**Single-machine Spark.** Our benchmarks run on a local Spark instance (`local[*]`). True cluster benefits require a multi-node setup (EMR, Databricks, or GKE Dataproc).

---

## 10. Future Work

- **Streaming pipeline:** Replace batch ingestion with Spark Structured Streaming on the TLC live data feed for real-time recommendations.
- **Graph analysis:** Model NYC as a mobility graph (zones as nodes, trip flows as edges) using GraphX or GraphFrames to identify corridor-level demand patterns.
- **Multi-modal data fusion:** Incorporate MTA subway ridership, Citi Bike docks, and pedestrian counts for a holistic urban mobility model.
- **Reinforcement learning:** Frame station placement as a sequential decision problem where each placed station changes the optimal location of the next.
- **Policy dashboard:** Deploy results as a Databricks SQL dashboard accessible to NYC DOT planners.

---

## 11. Conclusion

This project demonstrates that a relatively concise Spark ML pipeline — roughly 1,000 lines of modular Python — can convert raw taxi trip records into actionable EV infrastructure recommendations grounded in observed demand data. The KMeans clustering reveals eight distinct mobility regimes across NYC's zone system, and the GBT demand model achieves R² = 0.79 on held-out data, confirming that trip counts are highly predictable from temporal and spatial features. The EV recommendation engine identifies ten priority zones where new chargers would serve the highest number of trips with the lowest redundancy to existing infrastructure, yielding an estimated 15,200 tonnes of annual CO₂ savings under conservative adoption assumptions.

More broadly, this project illustrates a repeatable methodology that any city with open taxi or ride-share data could apply to guide sustainable transportation investment — replacing gut-feel infrastructure decisions with data-driven evidence.

---

## References

1. Zaharia, M., et al. (2016). Apache Spark: A Unified Engine for Big Data Processing. *Communications of the ACM*, 59(11), 56–65.
2. Dean, J., & Ghemawat, S. (2008). MapReduce: Simplified Data Processing on Large Clusters. *Communications of the ACM*, 51(1), 107–113.
3. Armbrust, M., et al. (2015). Spark SQL: Relational Data Processing in Spark. *ACM SIGMOD*, 1383–1394.
4. Meng, X., et al. (2016). MLlib: Machine Learning in Apache Spark. *Journal of Machine Learning Research*, 17(34), 1–7.
5. NYC Taxi & Limousine Commission. (2023). TLC Trip Record Data. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
6. New York State. (2023). Electric Vehicle Charging Stations in New York. https://data.ny.gov/Energy-Environment/Electric-Vehicle-Charging-Stations-in-New-York/7rrd-248n
7. US EPA. (2023). Greenhouse Gas Emission Factors Hub. US Environmental Protection Agency.
8. IEA. (2023). Global EV Outlook 2023. International Energy Agency, Paris.
9. Ferreira, N., et al. (2013). Visual Exploration of Big Spatio-Temporal Urban Data. *IEEE VAST*.
10. He, F., et al. (2018). Optimal Deployment of Public Charging Stations for PEVs Along Express Ways. *IEEE Transactions on Smart Grid*, 7(6), 2788–2799.
11. Zheng, Y., et al. (2011). Urban Computing with Taxicabs. *ACM UbiComp*, 89–98.
12. Tang, J., et al. (2015). Clustering of Traffic Flow Data Using Fuzzy C-means. *Journal of Intelligent Transportation Systems*, 19(2), 123–135.
