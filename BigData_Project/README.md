# NYC Taxi EV Charging Station Analysis
## Big Data Course Final Project — Spark ML Pipeline

> **Research Question:** How can a Spark-based big data pipeline analyze NYC taxi trip data to identify high-traffic zones where EV charging stations are needed most to reduce urban carbon emissions?

**Team:** Ankith Reddy Kasani · Ayush Manchanda

---

## Quick Start

```bash
# 1. Create virtual environment and install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the full pipeline (generates synthetic data automatically)
python main.py

# 3. Optional: scalability analysis
python main.py --run-scalability

# 4. Optional: use real NYC TLC data
python main.py --data-path /path/to/yellow_tripdata_2023-01.parquet
```

### Jupyter Notebook (Colab / Local)
```bash
pip install nbformat
python generate_notebook.py   # creates main.ipynb
jupyter notebook main.ipynb
```

---

## Project Structure

```
BigData_Project/
├── main.py                  ← full pipeline (entry point)
├── generate_notebook.py     ← creates main.ipynb
├── main.ipynb               ← self-contained notebook
├── requirements.txt
├── src/
│   ├── config.py            ← all settings + zone/EV station data
│   ├── data_generator.py    ← synthetic NYC taxi data
│   ├── data_pipeline.py     ← Spark ETL (load → clean → features → agg)
│   ├── ml_models.py         ← KMeans + LR + GBT (Spark MLlib)
│   ├── ev_recommender.py    ← gap analysis + priority ranking
│   ├── visualizer.py        ← all charts (matplotlib/seaborn)
│   └── scalability.py       ← Spark vs Pandas timing comparison
├── data/
│   ├── raw/                 ← input CSV
│   └── processed/           ← output Parquet
├── outputs/
│   ├── charts/              ← all PNG charts
│   ├── models/
│   └── results/             ← JSON summaries
├── report/
│   └── Final_Report.md
├── slides/
│   └── Presentation_Slides.md
└── docs/
    └── HOW_TO_RUN.md
```

---

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--num-records N` | 100,000 | Synthetic rows to generate |
| `--num-clusters K` | 8 | KMeans k |
| `--run-scalability` | off | Enable scalability benchmarks |
| `--data-path PATH` | auto | Real TLC CSV/Parquet path |

---

## Real Data Sources

| Dataset | URL |
|---------|-----|
| NYC TLC Yellow Taxi | https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page |
| NYC EV Charging Stations | https://data.ny.gov/Energy-Environment/Electric-Vehicle-Charging-Stations-in-New-York/7rrd-248n |

---

## Tech Stack

`Python 3.11` · `PySpark 4.x` · `Spark MLlib` · `Pandas` · `NumPy` · `Matplotlib` · `Seaborn` · `PyArrow`

---

## Outputs

After running, check:
- `outputs/charts/` — 9+ professional PNG charts
- `outputs/results/cluster_summary.json` — per-cluster stats
- `outputs/results/ev_recommendations.json` — ranked EV sites
- `outputs/results/regression_results.json` — model metrics
