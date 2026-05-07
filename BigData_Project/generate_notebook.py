#!/usr/bin/env python3
"""
Run once:  python generate_notebook.py
Produces:  main.ipynb  — fully self-contained, works in Colab with zero uploads.
"""
import nbformat as nbf, os

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11.0"},
}

def md(src):   return nbf.v4.new_markdown_cell(src)
def code(src): return nbf.v4.new_code_cell(src)

# ── CELL CONTENT ────────────────────────────────────────────────────────────

CELL_TITLE = """# NYC Taxi EV Charging Station Analysis
### Big Data Course Final Project — Apache Spark ML Pipeline

**Research Question:**
> *How can a Spark-based big data pipeline analyze NYC taxi trip data to identify
> high-traffic zones where EV charging stations are needed most to reduce urban carbon emissions?*

**Team:** Ankith Reddy Kasani · Ayush Manchanda

---
**Pipeline:** Data Generation → Spark ETL → KMeans Clustering → Demand Regression → EV Recommendations → Sustainability Impact
"""

CELL_INSTALL = """\
# ── Install dependencies (Colab / fresh environment) ─────────────────────
import subprocess, sys

REQUIRED = ['pyspark', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'scipy', 'pyarrow']
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])

print('All dependencies ready.')
"""

CELL_CONFIG = """\
import os, sys, time, math, warnings, json, logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.WARNING)
sns.set_theme(style='whitegrid')

# ── Project directories ───────────────────────────────────────────────────
BASE   = os.path.join(os.getcwd(), 'nyc_ev_project')
CHARTS = os.path.join(BASE, 'charts')
DATA   = os.path.join(BASE, 'data')
os.makedirs(CHARTS, exist_ok=True)
os.makedirs(DATA,   exist_ok=True)

# ── NYC Taxi Zone lookup: id → (name, borough, lat, lon, demand_weight) ──
NYC_ZONES = {
    161: ('Midtown Center',          'Manhattan',    40.7549, -73.9840, 10),
    162: ('Midtown East',            'Manhattan',    40.7549, -73.9680,  9),
    163: ('Midtown North',           'Manhattan',    40.7680, -73.9880,  9),
    224: ('Times Sq/Theatre Dist',   'Manhattan',    40.7590, -73.9845, 10),
    186: ('Penn Station',            'Manhattan',    40.7505, -73.9934,  9),
    100: ('Garment District',        'Manhattan',    40.7540, -73.9960,  8),
    232: ('Union Square',            'Manhattan',    40.7359, -73.9911,  8),
    261: ('World Trade Center',      'Manhattan',    40.7127, -74.0134,  8),
    234: ('Upper East Side South',   'Manhattan',    40.7680, -73.9590,  8),
    237: ('Upper West Side South',   'Manhattan',    40.7789, -73.9835,  7),
    87:  ('Flatiron',                'Manhattan',    40.7410, -73.9897,  7),
    45:  ('Chelsea',                 'Manhattan',    40.7465, -74.0014,  7),
    79:  ('East Village',            'Manhattan',    40.7264, -73.9805,  7),
    202: ('SoHo',                    'Manhattan',    40.7230, -74.0024,  7),
    114: ('Greenwich Village',       'Manhattan',    40.7286, -74.0013,  6),
    170: ('Murray Hill',             'Manhattan',    40.7490, -73.9780,  6),
    120: ('Harlem North',            'Manhattan',    40.8076, -73.9481,  5),
    246: ('Washington Heights',      'Manhattan',    40.8492, -73.9330,  4),
    17:  ('Bedford-Stuyvesant',      'Brooklyn',     40.6872, -73.9418,  5),
    97:  ('Greenpoint',              'Brooklyn',     40.7295, -73.9514,  5),
    67:  ('East Williamsburg',       'Brooklyn',     40.7137, -73.9338,  5),
    29:  ('Brooklyn Heights',        'Brooklyn',     40.6960, -73.9936,  6),
    25:  ('Boerum Hill',             'Brooklyn',     40.6877, -73.9857,  5),
    76:  ('Fort Greene',             'Brooklyn',     40.6920, -73.9752,  5),
    89:  ('Gowanus',                 'Brooklyn',     40.6771, -73.9928,  4),
    63:  ('DUMBO',                   'Brooklyn',     40.7030, -73.9893,  5),
    54:  ('Coney Island',            'Brooklyn',     40.5755, -73.9707,  3),
    33:  ('Bushwick North',          'Brooklyn',     40.7061, -73.9215,  4),
    7:   ('Astoria',                 'Queens',       40.7721, -73.9301,  6),
    117: ('Long Island City',        'Queens',       40.7471, -73.9417,  6),
    121: ('Queens Plaza',            'Queens',       40.7481, -73.9435,  5),
    73:  ('Flushing',                'Queens',       40.7675, -73.8330,  5),
    101: ('Jackson Heights',         'Queens',       40.7554, -73.8830,  5),
    129: ('LaGuardia Airport',       'Queens',       40.7773, -73.8740,  8),
    132: ('JFK Airport',             'Queens',       40.6413, -73.7781,  8),
    86:  ('Forest Hills',            'Queens',       40.7176, -73.8448,  4),
    102: ('Jamaica',                 'Queens',       40.6938, -73.8055,  4),
    59:  ('Concourse',               'Bronx',        40.8266, -73.9196,  3),
    78:  ('East Tremont',            'Bronx',        40.8416, -73.8790,  2),
    110: ('Melrose South',           'Bronx',        40.8130, -73.9214,  3),
    103: ('Kingsbridge',             'Bronx',        40.8699, -73.9043,  2),
    167: ('New Springville',         'Staten Island',40.5779, -74.1686,  2),
    223: ('Stapleton',               'Staten Island',40.6253, -74.0794,  2),
    1:   ('Newark Airport',          'EWR',          40.6895, -74.1745,  5),
}

# ── Existing EV stations: (name, lat, lon, num_chargers) ─────────────────
EXISTING_EV_STATIONS = [
    ('Midtown Manhattan Garage',   40.7540, -73.9870,  8),
    ('Times Square Hub',           40.7580, -73.9855, 12),
    ('JFK Airport Lot E',          40.6390, -73.7760, 20),
    ('LaGuardia Central Garage',   40.7770, -73.8735, 15),
    ('Brooklyn Downtown Lot',      40.6950, -73.9900,  6),
    ('Long Island City Depot',     40.7460, -73.9430, 10),
    ('Astoria Park & Charge',      40.7710, -73.9310,  4),
    ('Penn Station Garage',        40.7500, -73.9940,  8),
    ('Flatiron Charging Station',  40.7405, -73.9895,  6),
    ('World Trade Center Garage',  40.7115, -74.0125, 10),
    ('Upper East Side Depot',      40.7740, -73.9600,  6),
    ('Harlem 125th Street',        40.8080, -73.9470,  4),
    ('Bronx Hub Terminal',         40.8270, -73.9200,  4),
    ('Newark Airport Hub',         40.6900, -74.1750, 12),
    ('Greenpoint Depot',           40.7290, -73.9510,  4),
    ('SoHo Parking Garage',        40.7225, -74.0020,  6),
    ('Forest Hills Station',       40.7185, -73.8460,  4),
    ('Jamaica Center',             40.6945, -73.8060,  6),
    ('Flushing Main St',           40.7680, -73.8335,  4),
    ('Staten Island Ferry',        40.6436, -74.0736,  3),
]

# ── Constants ─────────────────────────────────────────────────────────────
NUM_RECORDS        = 100_000
NUM_CLUSTERS       = 8
TRAIN_RATIO        = 0.8
MIN_TRIPS_HOTSPOT  = 500
EV_RADIUS_KM       = 1.0
GASOLINE_CO2       = 404.0   # g CO2 per mile
EV_CO2             = 80.0    # g CO2 per mile
EV_ADOPTION        = 0.30

print(f'Config OK | {len(NYC_ZONES)} zones | {len(EXISTING_EV_STATIONS)} EV stations')
"""

CELL_SPARK = """\
from pyspark.sql import SparkSession

spark = (SparkSession.builder
    .appName('NYC_Taxi_EV_Analysis')
    .master('local[*]')
    .config('spark.driver.memory', '4g')
    .config('spark.sql.shuffle.partitions', '50')
    .config('spark.sql.adaptive.enabled', 'true')
    .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')
    .getOrCreate())
spark.sparkContext.setLogLevel('ERROR')
print(f'Spark {spark.version} | cores: {spark.sparkContext.defaultParallelism}')
"""

CELL_DATAGEN = """\
from datetime import datetime, timedelta

def generate_nyc_taxi_data(path, n=100_000, seed=42):
    rng = np.random.default_rng(seed)
    zone_ids = list(NYC_ZONES.keys())
    w = np.array([NYC_ZONES[z][4] for z in zone_ids], dtype=float); w /= w.sum()

    pu = rng.choice(zone_ids, size=n, p=w)
    do = np.where(rng.random(n) < 0.65,
                  rng.choice(zone_ids, size=n, p=w),
                  rng.choice(zone_ids, size=n))

    base = datetime(2023, 1, 1)
    hw   = np.array([.5,.3,.2,.18,.25,.65, 1.1,1.9,2.5,1.8,1.6,1.75,
                     1.85,1.95,1.85,1.75,1.9,2.3, 2.8,3.0,2.6,2.1,1.6,1.05])
    hw  /= hw.sum()
    hrs  = rng.choice(24, size=n, p=hw)
    days = rng.integers(0, 31, size=n)
    mins = rng.integers(0, 60, size=n)

    pu_dt = [base + timedelta(days=int(d), hours=int(h), minutes=int(m))
             for d, h, m in zip(days, hrs, mins)]

    dist  = np.clip(rng.lognormal(0.85, 0.75, n), 0.1, 60.0).round(2)
    speed = np.clip(rng.lognormal(2.35, 0.38, n), 2.0, 45.0)
    dur   = np.clip(dist / speed * 60, 1.0, 180.0)

    do_dt = [(pd.Timestamp(pu_dt[i]) + pd.Timedelta(minutes=float(dur[i]))).floor('s')
             for i in range(n)]

    fare   = np.clip(3.0 + dist*2.5 + dur*0.25 + rng.normal(0,.5,n), 2.5, 250.0).round(2)
    tips   = np.where(rng.random(n)<0.72, (fare*rng.uniform(.1,.28,n)).round(2), 0.0)
    tolls  = np.where(rng.random(n)<0.12, rng.uniform(.5,16,n).round(2), 0.0)
    cong   = np.where(rng.random(n)<0.62, 2.5, 0.0)
    total  = (fare + tips + tolls + cong + 0.8).round(2)
    pax    = rng.choice([1,2,3,4,5,6], size=n, p=[.55,.25,.10,.05,.03,.02])

    df = pd.DataFrame({
        'VendorID': rng.choice([1,2], size=n),
        'tpep_pickup_datetime':  pu_dt,
        'tpep_dropoff_datetime': do_dt,
        'passenger_count': pax,
        'trip_distance':   dist,
        'RatecodeID':      rng.choice([1,2,3,4,5,6], n, p=[.90,.04,.02,.01,.02,.01]),
        'PULocationID':    pu,
        'DOLocationID':    do,
        'payment_type':    rng.choice([1,2,3,4], n, p=[.65,.30,.03,.02]),
        'fare_amount':     fare,
        'extra':           rng.choice([0.,.5,1.], n, p=[.3,.5,.2]),
        'mta_tax':         0.5,
        'tip_amount':      tips,
        'tolls_amount':    tolls,
        'improvement_surcharge': 0.3,
        'total_amount':    total,
        'congestion_surcharge': cong,
    })
    df.to_csv(path, index=False)
    print(f'Generated {n:,} trips → {path}')
    return df

RAW_CSV = os.path.join(DATA, 'nyc_taxi_raw.csv')
if not os.path.exists(RAW_CSV):
    generate_nyc_taxi_data(RAW_CSV, n=NUM_RECORDS)
else:
    print(f'Data exists: {RAW_CSV}')
"""

CELL_ETL = """\
from pyspark.sql import functions as F

# ── Load ──────────────────────────────────────────────────────────────────
df = (spark.read
      .option('header', 'true')
      .option('inferSchema', 'true')
      .csv(RAW_CSV))
print(f'Raw rows: {df.count():,}')

# ── Clean ─────────────────────────────────────────────────────────────────
df = (df
    .dropna(subset=['tpep_pickup_datetime','tpep_dropoff_datetime',
                    'trip_distance','fare_amount','passenger_count','PULocationID'])
    .filter(F.col('trip_distance').between(0.1, 100.0))
    .filter(F.col('fare_amount').between(2.5, 500.0))
    .filter(F.col('passenger_count').between(1, 8))
    .filter(F.col('tpep_dropoff_datetime') > F.col('tpep_pickup_datetime'))
    .filter(F.col('PULocationID').between(1, 265))
    .filter(F.col('DOLocationID').between(1, 265))
)

# ── Temporal features ─────────────────────────────────────────────────────
df = (df
    .withColumn('pickup_hour',  F.hour('tpep_pickup_datetime'))
    .withColumn('pickup_dow',   F.dayofweek('tpep_pickup_datetime'))
    .withColumn('is_weekend',   F.when(F.col('pickup_dow').isin(1,7), 1).otherwise(0))
    .withColumn('is_rush_hour', F.when(
        (F.col('pickup_hour').between(7,9)) | (F.col('pickup_hour').between(16,19)), 1
    ).otherwise(0))
    .withColumn('trip_duration_min',
        (F.col('tpep_dropoff_datetime').cast('long') -
         F.col('tpep_pickup_datetime').cast('long')) / 60.0)
    .withColumn('speed_mph',
        F.when(F.col('trip_duration_min') > 0,
               F.col('trip_distance') / (F.col('trip_duration_min') / 60.0)).otherwise(None))
    .filter(F.col('trip_duration_min').between(1, 300))
    .filter(F.col('speed_mph').between(0.5, 80))
)

# ── Zone lookup join ──────────────────────────────────────────────────────
zone_rows = [(zid, info[0], info[1], float(info[2]), float(info[3]))
             for zid, info in NYC_ZONES.items()]
zone_schema = ['zone_id','zone_name','borough','zone_lat','zone_lon']
zone_sdf = spark.createDataFrame(zone_rows, schema=zone_schema)

df = (df
    .join(zone_sdf.select(
              F.col('zone_id').alias('_pu_id'),
              F.col('borough').alias('pu_borough'),
              F.col('zone_lat').alias('pu_lat'),
              F.col('zone_lon').alias('pu_lon')),
          df['PULocationID'] == F.col('_pu_id'), 'left')
    .drop('_pu_id')
)

df.cache()
clean_n = df.count()
print(f'Clean rows: {clean_n:,}  ({100*clean_n/df.count():.1f}% retained)')
df.select('pickup_hour','is_rush_hour','trip_duration_min','speed_mph','pu_borough').show(5)
"""

CELL_AGG = """\
# ── Zone-level aggregates (input to KMeans) ───────────────────────────────
df_zones = (df.groupBy('PULocationID')
    .agg(
        F.count('*')                           .alias('total_trips'),
        F.avg('trip_distance')                 .alias('avg_distance'),
        F.avg('fare_amount')                   .alias('avg_fare'),
        F.avg('speed_mph')                     .alias('avg_speed_mph'),
        F.avg('trip_duration_min')             .alias('avg_duration_min'),
        (F.sum('is_rush_hour')/F.count('*'))   .alias('rush_hour_fraction'),
        F.avg('is_weekend')                    .alias('weekend_fraction'),
        F.first('pu_lat')                      .alias('lat'),
        F.first('pu_lon')                      .alias('lon'),
        F.first('pu_borough')                  .alias('borough'),
    )
    .dropna()
)

# ── Zone×Hour aggregates (input to regression) ────────────────────────────
df_hourly = (df.groupBy('PULocationID','pickup_hour','pickup_dow')
    .agg(
        F.count('*')           .alias('trip_count'),
        F.avg('trip_distance') .alias('avg_distance'),
        F.avg('fare_amount')   .alias('avg_fare'),
        F.first('is_weekend')  .alias('is_weekend'),
        F.first('is_rush_hour').alias('is_rush_hour'),
    )
)

df_zones.cache(); df_hourly.cache()
print(f'Unique zones: {df_zones.count()}  |  Zone×Hour rows: {df_hourly.count():,}')
"""

CELL_EDA1 = """\
# Demand by hour
hourly_pdf = (df.groupBy('pickup_hour').count().orderBy('pickup_hour').toPandas())
RUSH = list(range(7,10)) + list(range(16,20))
colors = ['#e63946' if h in RUSH else '#457b9d' for h in hourly_pdf['pickup_hour']]

fig, ax = plt.subplots(figsize=(13,5))
ax.bar(hourly_pdf['pickup_hour'], hourly_pdf['count'], color=colors, edgecolor='white', width=0.85)
ax.set_xticks(range(24)); ax.set_xticklabels([f'{h:02d}' for h in range(24)])
ax.set_xlabel('Hour of Day'); ax.set_ylabel('Trip Count')
ax.set_title('NYC Taxi Demand by Hour   (red = rush hours)', fontweight='bold', fontsize=14)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{x:,.0f}'))
red_p  = mpatches.Patch(color='#e63946', label='Rush Hours (7-9am, 4-7pm)')
blue_p = mpatches.Patch(color='#457b9d', label='Off-Peak Hours')
ax.legend(handles=[red_p, blue_p])
ax.grid(axis='y', alpha=0.4); plt.tight_layout()
plt.savefig(f'{CHARTS}/01_demand_by_hour.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 01_demand_by_hour.png')
"""

CELL_EDA2 = """\
# Borough comparison
BOROUGH_COLORS = {'Manhattan':'#e63946','Brooklyn':'#457b9d','Queens':'#2a9d8f',
                  'Bronx':'#e9c46a','Staten Island':'#264653','EWR':'#6d6875'}
bp = (df_zones.groupBy('borough').agg(F.sum('total_trips').alias('trips'))
              .toPandas().sort_values('trips'))

fig, ax = plt.subplots(figsize=(10,5))
ax.barh(bp['borough'], bp['trips'],
        color=[BOROUGH_COLORS.get(b,'#888') for b in bp['borough']], edgecolor='white')
for i, (_, row) in enumerate(bp.iterrows()):
    ax.text(row['trips']+bp['trips'].max()*0.01, i, f\"{row['trips']:,.0f}\", va='center', fontsize=10)
ax.set_xlabel('Total Trips'); ax.set_title('Trip Volume by Borough', fontweight='bold', fontsize=14)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{x:,.0f}'))
ax.grid(axis='x', alpha=0.4); plt.tight_layout()
plt.savefig(f'{CHARTS}/02_borough_comparison.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 02_borough_comparison.png')
"""

CELL_KMEANS = """\
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

FEATURE_COLS = ['total_trips','avg_distance','avg_fare','avg_speed_mph',
                'rush_hour_fraction','weekend_fraction','avg_duration_min']

assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol='raw_features')
scaler    = StandardScaler(inputCol='raw_features', outputCol='features',
                           withMean=True, withStd=True)
kmeans    = KMeans(featuresCol='features', predictionCol='cluster',
                   k=NUM_CLUSTERS, maxIter=50, seed=42)
km_pipeline = Pipeline(stages=[assembler, scaler, kmeans])

km_model     = km_pipeline.fit(df_zones)
df_clustered = km_model.transform(df_zones)
df_clustered.cache()

evaluator  = ClusteringEvaluator(featuresCol='features', predictionCol='cluster')
silhouette = evaluator.evaluate(df_clustered)

cluster_summary = (df_clustered.groupBy('cluster')
    .agg(F.count('*')                .alias('num_zones'),
         F.sum('total_trips')        .alias('total_trips'),
         F.avg('total_trips')        .alias('avg_trips_per_zone'),
         F.avg('avg_distance')       .alias('avg_distance'),
         F.avg('rush_hour_fraction') .alias('rush_hour_fraction'),
         F.avg('lat')                .alias('centroid_lat'),
         F.avg('lon')                .alias('centroid_lon'),
         F.first('borough')          .alias('dominant_borough'))
    .orderBy('cluster').toPandas())

print(f'Silhouette score: {silhouette:.4f}')
print(cluster_summary[['cluster','num_zones','total_trips','rush_hour_fraction','dominant_borough']].to_string(index=False))
"""

CELL_CLUSTER_MAP = """\
PALETTE = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd',
           '#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']

zone_pdf = df_clustered.select('PULocationID','borough','lat','lon',
                                'total_trips','cluster').toPandas().dropna()

fig, ax = plt.subplots(figsize=(13,10))
ax.set_facecolor('#f0f4f8')
for c in sorted(zone_pdf['cluster'].unique()):
    sub = zone_pdf[zone_pdf['cluster']==c]
    sz  = 80 + sub['total_trips'] / zone_pdf['total_trips'].max() * 420
    ax.scatter(sub['lon'], sub['lat'], s=sz, c=PALETTE[int(c)%10],
               alpha=0.88, edgecolors='white', lw=0.5, label=f'Cluster {int(c)}')

ax.set_xlim(-74.30,-73.68); ax.set_ylim(40.48,40.95)
ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude')
ax.set_title('KMeans Cluster Map — NYC Taxi Pickup Zones\\n(circle size ∝ trip volume)',
             fontweight='bold', fontsize=14)
ax.legend(ncol=2, fontsize=9); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f'{CHARTS}/04_cluster_map.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 04_cluster_map.png')
"""

CELL_REGRESSION = """\
from pyspark.ml.regression import LinearRegression, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator

FEAT_COLS_REG = ['PULocationID','pickup_hour','pickup_dow',
                 'is_weekend','is_rush_hour','avg_distance','avg_fare']

df_reg   = df_hourly.dropna(subset=FEAT_COLS_REG+['trip_count']).filter(F.col('trip_count')>0)
df_reg.cache()
train_df, test_df = df_reg.randomSplit([TRAIN_RATIO, 1-TRAIN_RATIO], seed=42)

asm = VectorAssembler(inputCols=FEAT_COLS_REG, outputCol='features')
ev  = RegressionEvaluator(labelCol='trip_count', predictionCol='prediction')

def eval_model(pipeline, train, test, name):
    m    = pipeline.fit(train)
    pred = m.transform(test)
    rmse = ev.setMetricName('rmse').evaluate(pred)
    r2   = ev.setMetricName('r2').evaluate(pred)
    mae  = ev.setMetricName('mae').evaluate(pred)
    print(f'{name:<30} RMSE={rmse:.3f}  MAE={mae:.3f}  R²={r2:.4f}')
    return {'model':name, 'rmse':rmse, 'mae':mae, 'r2':r2}, m

lr_results, lr_model = eval_model(
    Pipeline(stages=[asm, LinearRegression(featuresCol='features',labelCol='trip_count',
                                           maxIter=100, regParam=0.01)]),
    train_df, test_df, 'Linear Regression')

gbt_results, gbt_model = eval_model(
    Pipeline(stages=[asm, GBTRegressor(featuresCol='features',labelCol='trip_count',
                                       maxIter=50, maxDepth=5, stepSize=0.1, seed=42)]),
    train_df, test_df, 'Gradient Boosted Trees')

fi   = gbt_model.stages[-1].featureImportances
feat_imp = dict(zip(FEAT_COLS_REG, [float(x) for x in fi]))
reg_results = {'linear_regression': lr_results, 'gbt': gbt_results,
               'feature_importances': feat_imp}
df_reg.unpersist()
"""

CELL_REG_CHART = """\
fig, axes = plt.subplots(1, 2, figsize=(13,5))
metrics  = [('rmse','RMSE (lower=better)'), ('r2','R² Score (higher=better)')]
for ax, (met, lbl) in zip(axes, metrics):
    vals  = [lr_results[met], gbt_results[met]]
    bars  = ax.bar(['Linear\\nRegression','GBT\\nRegressor'], vals,
                   color=['#457b9d','#e63946'], edgecolor='white', width=0.5)
    for b in bars:
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(abs(v) for v in vals)*0.02,
                f'{b.get_height():.3f}', ha='center', fontsize=12, fontweight='bold')
    ax.set_title(lbl, fontweight='bold'); ax.grid(axis='y', alpha=0.4)
    if met=='r2': ax.set_ylim(min(0,min(vals))-0.1, 1.1)

fig.suptitle('Demand Prediction — Model Comparison', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{CHARTS}/08_regression_comparison.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 08_regression_comparison.png')
"""

CELL_EV_RECOMMENDER = """\
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1,p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2-lon1); dp = math.radians(lat2-lat1)
    a  = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def nearest_charger_km(lat, lon):
    return min(haversine_km(lat,lon,s[1],s[2]) for s in EXISTING_EV_STATIONS)

def chargers_within(lat, lon, radius=EV_RADIUS_KM):
    return sum(1 for s in EXISTING_EV_STATIONS
               if haversine_km(lat,lon,s[1],s[2]) <= radius)

# Score every zone
zpdf = df_clustered.select('PULocationID','borough','lat','lon',
                            'total_trips','rush_hour_fraction',
                            'avg_distance','cluster').toPandas().dropna(subset=['lat','lon'])

max_trips = zpdf['total_trips'].max()
zpdf['demand_score'] = (zpdf['total_trips']/max_trips*0.7 +
                        zpdf['rush_hour_fraction']*0.3)
zpdf['nearest_km']   = zpdf.apply(lambda r: nearest_charger_km(r['lat'],r['lon']), axis=1)
zpdf['chargers_1km'] = zpdf.apply(lambda r: chargers_within(r['lat'],r['lon']),   axis=1)

max_d = zpdf['nearest_km'].clip(upper=30).max()
zpdf['gap_score']      = zpdf['nearest_km'].clip(upper=30) / max_d
zpdf['priority_score'] = 0.60*zpdf['demand_score'] + 0.40*zpdf['gap_score']

# Filter: hotspot + underserved
recs = (zpdf[(zpdf['total_trips'] >= MIN_TRIPS_HOTSPOT) & (zpdf['chargers_1km'] < 2)]
        .sort_values('priority_score', ascending=False)
        .head(10).reset_index(drop=True))
recs['rank']      = recs.index + 1
recs['zone_name'] = recs['PULocationID'].map(lambda z: NYC_ZONES.get(z,('Zone '+str(z),))[0])

# CO2 estimate
co2_save = (GASOLINE_CO2 - EV_CO2) * recs['avg_distance']
recs['annual_trips']    = (recs['total_trips'] * 12).astype(int)
recs['co2_saved_tonnes']= (recs['annual_trips'] * EV_ADOPTION * co2_save / 1_000_000).round(1)

print('\\n' + '='*62)
print(f\"  {'Rank':<5} {'Zone':<32} {'Borough':<15} {'Score':>6}\")
print('-'*62)
for _, r in recs.iterrows():
    print(f\"  {int(r['rank']):<5} {r['zone_name']:<32} {r['borough']:<15} {r['priority_score']:>6.3f}\")
print('-'*62)
print(f\"  Total estimated CO2 saved: {recs['co2_saved_tonnes'].sum():,.1f} tonnes/year\")
print('='*62)
"""

CELL_EV_MAP = """\
ev_lats = [s[1] for s in EXISTING_EV_STATIONS]
ev_lons = [s[2] for s in EXISTING_EV_STATIONS]

fig, ax = plt.subplots(figsize=(13,10))
ax.set_facecolor('#eaf4fb')
ax.scatter(zpdf['lon'], zpdf['lat'], s=40, c='#cccccc', alpha=0.6,
           label='All Zones', edgecolors='white', lw=0.3, zorder=2)
ax.scatter(ev_lons, ev_lats, s=170, c='#1f77b4', marker='^', alpha=0.9,
           label='Existing EV Stations', edgecolors='white', lw=0.8, zorder=4)
ax.scatter(recs['lon'], recs['lat'], s=340, c='#e63946', marker='*', alpha=1.0,
           label='Recommended New Sites', edgecolors='white', lw=0.6, zorder=5)

for _, r in recs.head(5).iterrows():
    ax.annotate(f\"#{int(r['rank'])} {r['zone_name'][:17]}\",
                (r['lon'], r['lat']), xytext=(8,8), textcoords='offset points',
                fontsize=8, color='#c0392b',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.78))

ax.set_xlim(-74.30,-73.68); ax.set_ylim(40.48,40.95)
ax.set_title('EV Charging Gap Analysis — NYC\\n★ Recommended New Sites  ▲ Existing Stations',
             fontweight='bold', fontsize=14)
ax.legend(fontsize=11, loc='lower left'); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f'{CHARTS}/06_ev_map.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 06_ev_map.png')
"""

CELL_SUSTAINABILITY = """\
fig, ax = plt.subplots(figsize=(11,7))
df_plot = recs.sort_values('co2_saved_tonnes')
colors  = plt.cm.Greens(np.linspace(0.4, 0.9, len(df_plot)))
ax.barh(df_plot['zone_name'], df_plot['co2_saved_tonnes'],
        color=colors, edgecolor='white')
for i, (_, r) in enumerate(df_plot.iterrows()):
    ax.text(r['co2_saved_tonnes']+df_plot['co2_saved_tonnes'].max()*0.01, i,
            f\"{r['co2_saved_tonnes']:.1f} t\", va='center', fontsize=10)

total = recs['co2_saved_tonnes'].sum()
ax.set_xlabel('Annual CO₂ Saved (metric tonnes)', fontsize=13)
ax.set_title(f'Sustainability Impact — Estimated CO₂ Savings\\nTotal across top-10 zones: {total:,.1f} t/year',
             fontweight='bold', fontsize=14)
ax.grid(axis='x', alpha=0.4); plt.tight_layout()
plt.savefig(f'{CHARTS}/07_sustainability.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 07_sustainability.png')
"""

CELL_SCALABILITY = """\
import time as _time

def spark_pipeline(csv_path):
    t = _time.perf_counter()
    d = (spark.read.option('header','true').option('inferSchema','true').csv(csv_path)
           .dropna(subset=['trip_distance','fare_amount'])
           .filter(F.col('trip_distance').between(0.1,100))
           .filter(F.col('fare_amount').between(2.5,500))
           .withColumn('pickup_hour', F.hour('tpep_pickup_datetime'))
           .withColumn('is_rush_hour', F.when(
               (F.col('pickup_hour').between(7,9))|(F.col('pickup_hour').between(16,19)),1).otherwise(0))
           .groupBy('PULocationID')
           .agg(F.count('*').alias('trips'), F.avg('trip_distance').alias('avg_dist')))
    d.count()   # force evaluation
    return round(_time.perf_counter()-t, 2)

def pandas_pipeline(csv_path):
    t = _time.perf_counter()
    d = pd.read_csv(csv_path)
    d = d.dropna(subset=['trip_distance','fare_amount'])
    d = d[(d['trip_distance'].between(0.1,100)) & (d['fare_amount'].between(2.5,500))]
    d['pickup_hour'] = pd.to_datetime(d['tpep_pickup_datetime']).dt.hour
    d['is_rush_hour'] = d['pickup_hour'].apply(lambda h: 1 if 7<=h<=9 or 16<=h<=19 else 0)
    d.groupby('PULocationID').agg(trips=('trip_distance','count'),
                                   avg_dist=('trip_distance','mean'))
    return round(_time.perf_counter()-t, 2)

SIZES    = [5_000, 25_000, 75_000, 150_000]
spark_t  = []; pandas_t = []

for n in SIZES:
    path = os.path.join(DATA, f'sample_{n}.csv')
    if not os.path.exists(path):
        generate_nyc_taxi_data(path, n=n, seed=7)
    st = spark_pipeline(path);  spark_t.append(st)
    pt = pandas_pipeline(path); pandas_t.append(pt)
    print(f'n={n:>7,}  Spark={st:.2f}s  Pandas={pt:.2f}s  Speedup={pt/st:.2f}×')

# Chart
fig, (ax1,ax2) = plt.subplots(1,2, figsize=(14,6))
ax1.plot(SIZES, spark_t,  'o-', color='#e63946', lw=2.5, ms=8, label='Spark')
ax1.plot(SIZES, pandas_t, 's--',color='#457b9d', lw=2.5, ms=8, label='Pandas (single-thread)')
ax1.set_xlabel('Dataset Size (rows)'); ax1.set_ylabel('Time (s)')
ax1.set_title('Processing Time vs Dataset Size', fontweight='bold')
ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{x/1000:.0f}k'))
ax1.legend(); ax1.grid(alpha=0.4)

speedup = [p/s for p,s in zip(pandas_t,spark_t)]
ax2.plot(SIZES, speedup, 'D-', color='#2ca02c', lw=2.5, ms=8)
ax2.axhline(1.0, ls='--', color='#888', lw=1.5, label='Break-even (1×)')
ax2.set_xlabel('Dataset Size (rows)'); ax2.set_ylabel('Speedup')
ax2.set_title('Spark Speedup over Pandas', fontweight='bold')
ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x,_: f'{x/1000:.0f}k'))
ax2.legend(); ax2.grid(alpha=0.4)

fig.suptitle('Scalability — Apache Spark vs Pandas', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{CHARTS}/11_scalability.png', dpi=140, bbox_inches='tight')
plt.show(); print('Saved: 11_scalability.png')
"""

CELL_SUMMARY = """\
print('='*60)
print('  PROJECT COMPLETE')
print(f'  Clean records    : {clean_n:>10,}')
print(f'  Clusters found   : {NUM_CLUSTERS}')
print(f'  LR  R²           : {lr_results[\"r2\"]:>10.4f}')
print(f'  GBT R²           : {gbt_results[\"r2\"]:>10.4f}')
print(f'  EV sites ranked  : {len(recs)}')
print(f'  CO₂ savings est  : {recs[\"co2_saved_tonnes\"].sum():>8,.1f} t/year')
print(f'  Charts saved to  : {CHARTS}')
print('='*60)
import os; charts = sorted(os.listdir(CHARTS))
print(f'  Charts ({len(charts)}): {charts}')
spark.stop()
"""

# ── BUILD NOTEBOOK ──────────────────────────────────────────────────────────
nb.cells = [
    md(CELL_TITLE),
    md("## Setup — Install & Configure"),
    code(CELL_INSTALL),
    code(CELL_CONFIG),
    md("## 1 · Spark Session"),
    code(CELL_SPARK),
    md("## 2 · Data Generation\nSynthetic NYC TLC-schema trips calibrated to real Jan-2023 statistics."),
    code(CELL_DATAGEN),
    md("## 3 · ETL — Clean & Feature Engineering"),
    code(CELL_ETL),
    code(CELL_AGG),
    md("## 4 · Exploratory Data Analysis"),
    code(CELL_EDA1),
    code(CELL_EDA2),
    md("## 5 · KMeans Clustering\nGroups the 44 pickup zones into 8 mobility regimes."),
    code(CELL_KMEANS),
    code(CELL_CLUSTER_MAP),
    md("## 6 · Demand Prediction (Regression)\nTwo models predict `trip_count` per zone per hour."),
    code(CELL_REGRESSION),
    code(CELL_REG_CHART),
    md("## 7 · EV Charging Recommendation Engine"),
    code(CELL_EV_RECOMMENDER),
    code(CELL_EV_MAP),
    code(CELL_SUSTAINABILITY),
    md("## 8 · Scalability Analysis — Spark vs Pandas"),
    code(CELL_SCALABILITY),
    md("## 9 · Summary & Conclusions"),
    code(CELL_SUMMARY),
]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.ipynb')
nbf.write(nb, out)
print(f'main.ipynb written  ({len(nb.cells)} cells)')
