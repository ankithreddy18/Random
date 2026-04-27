# How to Run — Step-by-Step Guide

## Prerequisites
- Python 3.9+
- Java 11+ (required by Spark) — verify: `java -version`
- 4 GB free RAM minimum

## Local Machine

```bash
git clone <repo-url>
cd BigData_Project

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Default run (100k synthetic records, 8 clusters)
python main.py

# Custom run
python main.py --num-records 500000 --num-clusters 10 --run-scalability
```

## Google Colab

1. Upload the entire `BigData_Project/` folder to your Drive.
2. Open `main.ipynb` in Colab.
3. Run the first cell (`pip install pyspark …`) — takes ~90 seconds.
4. Run all cells in order.

```python
# Mount Drive if needed
from google.colab import drive
drive.mount('/content/drive')
import os
os.chdir('/content/drive/MyDrive/BigData_Project')
```

## Using Real NYC TLC Data

```bash
# Download Jan 2023 Yellow Taxi Parquet (~500 MB)
curl -O https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet

python main.py --data-path yellow_tripdata_2023-01.parquet --num-clusters 10
```

## Databricks

```python
# In a Databricks notebook — SparkSession already exists
import sys; sys.path.insert(0, '/dbfs/FileStore/BigData_Project/src')
from config import Config
from data_pipeline import DataPipeline
# spark is pre-defined by Databricks
```

## Expected Runtime (local, 8-core)

| Records | ETL | KMeans | Regression | Total |
|---------|-----|--------|-----------|-------|
| 100k    | ~40s | ~30s | ~60s | ~2.5 min |
| 500k    | ~90s | ~45s | ~90s | ~4 min   |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `java: command not found` | Install Java 11: `sudo apt install openjdk-11-jdk` |
| `OutOfMemoryError` | Reduce `--num-records` or increase `spark.driver.memory` in `src/config.py` |
| `ModuleNotFoundError: config` | Ensure you `cd BigData_Project/` before running |
| Charts not showing in notebook | Run `%matplotlib inline` in Jupyter |
