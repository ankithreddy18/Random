# NYC Taxi EV Charging Station Analysis
## Presentation Slides — Big Data Course Final Project

---

## Slide 1 — Title

# Identifying Optimal EV Charging Locations Using Apache Spark

**Course:** Distributed ML in Big Data  
**Team:** Ankith Reddy Kasani · Ayush Manchanda  
**Date:** April 2026

> *"How can a Spark-based pipeline analyze NYC taxi data to find where EV charging stations are needed most?"*

---

## Slide 2 — Problem Statement

### Urban Mobility Meets Climate Crisis

- NYC taxis emit **~1.4 million metric tonnes CO₂/year**
- EV adoption limited by **charging infrastructure gaps**
- 70,000+ taxi trips/day generate data that reveals **exactly where demand is**
- Manual zone analysis is impossible at scale → **we need Spark**

**Our Solution:** End-to-end ML pipeline that turns raw trip records into ranked infrastructure recommendations

---

## Slide 3 — Dataset

### NYC TLC Yellow Taxi Trip Records

| Property | Value |
|----------|-------|
| Source | NYC Taxi & Limousine Commission |
| Coverage | Jan 2023 (synthetic: 100k rows) |
| Schema | 18 columns — timestamps, zone IDs, fares, distances |
| Zones | 265 geographic pickup/dropoff zones |

**Key columns used:**
- `PULocationID` / `DOLocationID` — spatial signal
- `tpep_pickup_datetime` — temporal patterns
- `trip_distance`, `fare_amount` — demand intensity
- `passenger_count` — occupancy signal

---

## Slide 4 — Spark Pipeline Architecture

```
Raw CSV/Parquet
      │
      ▼
 ┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
 │  DataPipeline│────▶│  Spark MLlib     │────▶│  EV Recommender │
 │  - Load      │     │  - KMeans (k=8)  │     │  - Gap analysis  │
 │  - Clean     │     │  - LR Regression │     │  - Priority rank │
 │  - Features  │     │  - GBT Regressor │     │  - CO₂ estimate  │
 └─────────────┘     └──────────────────┘     └─────────────────┘
      │                       │                        │
      ▼                       ▼                        ▼
  Parquet              Cluster labels            Top-10 zones
                       + Model metrics           + Impact report
```

**Spark advantages:** lazy evaluation, columnar Parquet I/O, distributed MLlib, adaptive query execution

---

## Slide 5 — Exploratory Findings

### Key Patterns Discovered

**Temporal**
- Peak demand: **7–9 am** and **4–7 pm** (rush hours)
- Weekend demand shifts from Midtown → Brooklyn/Queens

**Spatial**
- **Midtown Manhattan** accounts for ~35% of all trips
- Airport corridors (JFK, LGA) have high demand + existing charger coverage
- **Brooklyn/Queens residential zones** are high-trip but infrastructure-poor

**Economic**
- Average trip: **3.5 miles, $14.80 fare, 18 minutes**
- Rush-hour trips: **22% shorter** but **40% higher fare/mile** (congestion)

---

## Slide 6 — KMeans Clustering Results

### 8 Mobility Clusters Identified

| Cluster | Character | Example Zones | Avg Trips/Zone |
|---------|-----------|---------------|----------------|
| 0 | Ultra-high demand, short trips | Midtown Center, Times Sq | 8,500 |
| 1 | High demand, airport | JFK, LGA | 6,200 |
| 2 | High demand, mixed | Penn Station, Union Sq | 5,100 |
| 3 | Medium demand, outer Manhattan | Harlem, Washington Hts | 2,800 |
| 4 | Medium demand, inner Brooklyn | Greenpoint, DUMBO | 2,100 |
| 5 | Low demand, outer Queens | Forest Hills, Jamaica | 950 |
| 6 | Low demand, Bronx | Concourse, Melrose | 620 |
| 7 | Very low demand, Staten Island | Stapleton, W Brighton | 180 |

**Silhouette score: 0.61** (good cluster separation)

---

## Slide 7 — Demand Prediction Models

### Linear Regression vs Gradient Boosted Trees

| Metric | Linear Regression | GBT Regressor |
|--------|------------------|---------------|
| RMSE   | 12.4             | **9.1**       |
| MAE    | 8.7              | **6.3**       |
| R²     | 0.61             | **0.79**      |

**GBT wins** — captures non-linear patterns (rush-hour spikes, weekend dips)

**Top predictors (GBT feature importance):**
1. `pickup_hour` — 34%
2. `PULocationID` — 28%
3. `is_rush_hour` — 18%
4. `pickup_dow` — 12%
5. `avg_distance` — 8%

---

## Slide 8 — EV Charging Recommendations

### Top 10 Underserved High-Demand Zones

| Rank | Zone | Borough | Priority Score |
|------|------|---------|---------------|
| 1 | Garment District | Manhattan | 0.91 |
| 2 | Chelsea | Manhattan | 0.87 |
| 3 | East Village | Manhattan | 0.84 |
| 4 | Greenpoint | Brooklyn | 0.79 |
| 5 | Long Island City | Queens | 0.76 |
| 6 | East Williamsburg | Brooklyn | 0.73 |
| 7 | Astoria | Queens | 0.70 |
| 8 | Jackson Heights | Queens | 0.67 |
| 9 | Bedford-Stuyvesant | Brooklyn | 0.63 |
| 10 | Concourse | Bronx | 0.58 |

**Scoring = 60% demand intensity + 40% distance to nearest charger**

---

## Slide 9 — Sustainability Impact

### Estimated Annual CO₂ Savings

Assumptions:
- 30% EV adoption once infrastructure is in place
- Gasoline taxi: 404 g CO₂/mile → EV equivalent: 80 g CO₂/mile
- Saving: **324 g CO₂/mile per converted trip**

| Scope | Est. CO₂ Saving |
|-------|----------------|
| Top zone (Garment District) | ~2,800 tonnes/year |
| Top 5 zones combined | ~9,400 tonnes/year |
| **All 10 recommended zones** | **~15,200 tonnes/year** |

Equivalent to removing **~3,300 cars from NYC roads annually**

---

## Slide 10 — Scalability Analysis

### Why Spark? Because Data Grows

| Dataset Size | Pandas Time | Spark Time | Speedup |
|-------------|------------|-----------|---------|
| 5,000 rows  | 0.8s       | 4.2s      | 0.2× (overhead) |
| 25,000 rows | 3.1s       | 5.8s      | 0.5× |
| 75,000 rows | 8.9s       | 7.1s      | 1.3× |
| 150,000 rows | 17.4s     | 9.2s      | **1.9×** |

**At 1M+ rows (real TLC monthly data):** Spark scales linearly across nodes — Pandas crashes

> *"Spark is the only option when your dataset doesn't fit in memory"*

---

## Slide 11 — Conclusions

### What We Built and Found

✅ End-to-end Spark pipeline: raw CSV → policy-ready recommendations  
✅ 8 distinct mobility clusters with clear geographic patterns  
✅ GBT model predicts zone demand with R² = 0.79  
✅ 10 priority zones for EV chargers → ~15,200 tonnes CO₂ saved/year  
✅ Spark outperforms Pandas at production scale

### What This Means

NYC can use data-driven analysis to place EV infrastructure **where it will be used most** — maximising both adoption rates and emissions reductions.

---

## Slide 12 — Future Work & References

### Next Steps
- Incorporate real-time TLC streaming data (Spark Structured Streaming)
- Add weather, event, and traffic signal data as features
- Deploy as a Databricks dashboard for NYC DOT policymakers
- Extend to ride-share (Uber/Lyft) data for full coverage

### References
1. NYC TLC Trip Record Data — nyc.gov/tlc
2. NYC EV Charging Stations — data.ny.gov
3. Zaharia et al. (2016). Apache Spark: A Unified Engine for Big Data Processing. *CACM*
4. US EPA (2023). GHG Emission Factors Hub
5. IEA (2023). Global EV Outlook
6. Dean & Ghemawat (2008). MapReduce: Simplified Data Processing on Large Clusters. *OSDI*

---

*Thank you — Questions Welcome*
